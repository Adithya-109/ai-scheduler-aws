"""Observed-runtime memory keyed by code hash.

The static analyser is blind to some programs (opaque loop bounds, exec, data
dependent control flow). A script that has already run is the best predictor
of its own runtime, so measured times from the decision log override the
regression for the side(s) where we have enough clean observations.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

OBSERVED_SIGMA_LOG10 = 0.05  # run-to-run noise of a repeated job, far below model error


class RuntimeHistory:
    def __init__(self, min_obs: int = 2, max_obs: int = 50):
        self.min_obs, self.max_obs = min_obs, max_obs
        self._t: dict[tuple[str, str], list[float]] = defaultdict(list)

    def observe(self, code_hash: str, target: str, seconds, ok: bool = True) -> None:
        # Failed or timed-out runs measure the failure, not the workload.
        if not ok or seconds is None or seconds < 0 or target not in ("edge", "cloud"):
            return
        buf = self._t[(code_hash, target)]
        buf.append(float(seconds))
        del buf[:-self.max_obs]

    def median(self, code_hash: str, target: str) -> float | None:
        buf = self._t.get((code_hash, target), [])
        return statistics.median(buf) if len(buf) >= self.min_obs else None

    @classmethod
    def from_records(cls, records, **kw) -> "RuntimeHistory":
        h = cls(**kw)
        for r in records:
            h.observe(r.get("code_hash", ""), r.get("target"), r.get("compute_time_s"),
                      ok=not r.get("timed_out", False) and r.get("returncode", 0) == 0)
        return h

    @classmethod
    def from_log(cls, log, **kw) -> "RuntimeHistory":
        return cls.from_records(log.read(), **kw)
