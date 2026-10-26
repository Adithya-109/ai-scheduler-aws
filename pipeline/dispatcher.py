"""Run a job where the scheduler says, with failure handling.

* cloud errors/timeouts fall back to the edge worker;
* a circuit breaker stops sending to a cloud node that keeps failing;
* every outcome is appended to the decision log;
* optional epsilon-greedy exploration on low-confidence decisions, so the
  models also see the side they would otherwise never observe.
"""
from __future__ import annotations

import random
import time

import config
from pipeline.scheduler import OffloadingScheduler


class WorkerError(Exception):
    pass


class WorkerClient:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 65.0, session=None):
        self.url = config.execute_url(base_url)
        self.health_url = config.health_url(base_url)
        self.headers = config.auth_headers(api_key)
        self.timeout = timeout
        self.session = session

    def execute(self, code: str) -> tuple[dict, float]:
        """Return (worker response, wall seconds including network)."""
        import requests

        post = self.session.post if self.session is not None else requests.post
        t0 = time.perf_counter()
        try:
            r = post(self.url, json={"code": code}, headers=self.headers, timeout=self.timeout)
        except requests.RequestException as e:
            raise WorkerError(f"{type(e).__name__}: {e}") from e
        wall = time.perf_counter() - t0
        if r.status_code != 200:
            raise WorkerError(f"HTTP {r.status_code}: {r.text[:200]}")
        try:
            return r.json(), wall
        except ValueError as e:
            raise WorkerError("worker returned non-JSON") from e


class CircuitBreaker:
    """Open after ``threshold`` consecutive failures; allow a probe after ``reset_s``."""

    def __init__(self, threshold: int = 3, reset_s: float = 30.0, clock=time.monotonic):
        self.threshold, self.reset_s, self._clock = threshold, reset_s, clock
        self.failures = 0
        self.opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        return self.opened_at is not None and self._clock() - self.opened_at < self.reset_s

    def allow(self) -> bool:
        return not self.is_open  # after reset_s the next call is the half-open probe

    def record_success(self) -> None:
        self.failures, self.opened_at = 0, None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = self._clock()


class Dispatcher:
    def __init__(self, scheduler: OffloadingScheduler, edge: WorkerClient, cloud: WorkerClient | None,
                 log=None, breaker: CircuitBreaker | None = None, epsilon: float = 0.0,
                 explore_below_confidence: float = 0.8, rng: random.Random | None = None):
        self.scheduler, self.edge, self.cloud = scheduler, edge, cloud
        self.log = log
        self.breaker = breaker or CircuitBreaker()
        self.epsilon, self.explore_below = epsilon, explore_below_confidence
        self.rng = rng or random.Random()
        self.cloud_load: dict | None = None

    def refresh_health(self) -> dict | None:
        """Ping the cloud /health: updates the live RTT and the load snapshot."""
        if self.cloud is None or self.scheduler.rtt_tracker is None:
            return None
        body = self.scheduler.rtt_tracker.probe(self.cloud.health_url)
        if body is not None:
            self.cloud_load = {"active_jobs": body.get("active_jobs", 0), "cpu_count": body.get("cpu_count", 1)}
            self.breaker.record_success()
        else:
            self.breaker.record_failure()
        return body

    def run(self, code: str) -> dict:
        plan = self.scheduler.schedule(code, cloud_load=self.cloud_load)
        if "error" in plan:
            return plan

        target = "cloud" if plan["decision"] == "CLOUD" else "edge"
        explored, fallback = False, None
        if (self.epsilon > 0 and plan["confidence"] < self.explore_below
                and self.rng.random() < self.epsilon):
            target, explored = ("edge" if target == "cloud" else "cloud"), True

        if target == "cloud":
            if self.cloud is None:
                target, fallback = "edge", "cloud_not_configured"
            elif not self.breaker.allow():
                target, fallback = "edge", "circuit_open"

        data = wall = None
        if target == "cloud":
            try:
                data, wall = self.cloud.execute(code)
                self.breaker.record_success()
            except WorkerError as e:
                self.breaker.record_failure()
                target, fallback = "edge", f"cloud_error: {e}"
        if data is None:
            data, wall = self.edge.execute(code)  # an edge failure is a real error: let it raise

        compute = data.get("execution_time_seconds")
        result = {
            **plan,
            "target": target,
            "fallback": fallback,
            "explored": explored,
            "worker": data,
            "wall_time_s": wall,
            "compute_time_s": compute,
        }
        if self.scheduler.history is not None:
            self.scheduler.history.observe(
                plan["code_hash"], target, compute,
                ok=data.get("returncode", 0) == 0 and not data.get("timed_out", False))
        if self.log is not None:
            self.log.record(
                code_hash=plan["code_hash"], feature_version=plan["feature_version"],
                features=plan["features"], predictions=plan["predictions"], decision=plan["decision"],
                confidence=plan["confidence"], target=target, fallback=fallback is not None,
                fallback_reason=fallback, explored=explored, wall_time_s=wall, compute_time_s=compute,
                returncode=data.get("returncode", 0), timed_out=data.get("timed_out", False))
        return result
