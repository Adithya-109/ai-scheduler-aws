"""Live round-trip-time estimate to the cloud worker (EWMA over /health pings)."""
from __future__ import annotations

import threading
import time


class RttTracker:
    def __init__(self, initial_s: float | None = None, alpha: float = 0.3):
        self.alpha = alpha
        self._value = initial_s
        self._lock = threading.Lock()

    @property
    def value(self) -> float | None:
        with self._lock:
            return self._value

    def update(self, sample_s: float) -> float:
        with self._lock:
            self._value = sample_s if self._value is None else (
                self.alpha * sample_s + (1 - self.alpha) * self._value)
            return self._value

    def probe(self, health_url: str, headers: dict | None = None, timeout: float = 3.0,
              session=None) -> dict | None:
        """GET /health once; update the EWMA with the round trip. Returns the
        worker's health JSON (with ``rtt_s`` added) or None if unreachable."""
        import requests

        getter = session.get if session is not None else requests.get
        t0 = time.perf_counter()
        try:
            r = getter(health_url, headers=headers or {}, timeout=timeout)
            elapsed = time.perf_counter() - t0
            if r.status_code != 200:
                return None
            body = r.json()
        except (requests.RequestException, ValueError):
            return None
        self.update(elapsed)
        body["rtt_s"] = elapsed
        return body
