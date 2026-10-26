"""Latency prediction and the routing rule.

Decision (the only one, no secondary classifier that can veto it):

    CLOUD  iff  predicted_cloud_compute + RTT + transfer + cloud_queue
                  <  (predicted_edge_compute + edge_queue) * (1 - margin)

``confidence`` is the probability, under the model's measured out-of-fold error
(sigma in log10 seconds, stored at training time), that the *chosen* side really
is the faster one. It is therefore >= 0.5 whenever margin == 0.
"""
from __future__ import annotations

import json
import logging
import math
import os
import warnings

import joblib
import numpy as np

log = logging.getLogger(__name__)
EPS = 1e-6
LN10 = math.log(10.0)


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def queue_penalty(load: dict | None, compute_s: float) -> float:
    """Heuristic extra wait when a node's slots are already full.

    ``load`` is {"active_jobs": int, "cpu_count": int}. With every slot busy a
    new job waits roughly one job's duration divided by parallelism. This is a
    simple estimate, not a queueing model.
    """
    if not load:
        return 0.0
    cpus = max(int(load.get("cpu_count") or 1), 1)
    busy_over = max(0, int(load.get("active_jobs") or 0) - cpus + 1)
    return busy_over * compute_s / cpus


class LatencyPredictor:
    def __init__(self, network_latency_cloud_ms: float | None = None, margin: float = 0.0,
                 bandwidth_bytes_per_s: float | None = None, models_dir: str | None = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_dir = models_dir or os.path.join(base_dir, "models")
        self.margin = float(margin)
        self.bandwidth = bandwidth_bytes_per_s
        self.metadata: dict = {}
        meta_path = os.path.join(models_dir, "training_metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as fh:
                self.metadata = json.load(fh)

        from pipeline.feature_extractor import FEATURE_COLUMNS
        self.feature_cols = self.metadata.get("feature_columns", FEATURE_COLUMNS)
        self.sigma_edge = float(self.metadata.get("sigma_edge_log10", 0.2))
        self.sigma_cloud = float(self.metadata.get("sigma_cloud_log10", 0.2))
        self.default_rtt = float(self.metadata.get("measured_rtt_seconds", 0.12))
        self.fixed_rtt = None if network_latency_cloud_ms is None else network_latency_cloud_ms / 1000.0
        # kept for backwards compatibility with callers that read the attribute
        self.network_latency_cloud = self.fixed_rtt if self.fixed_rtt is not None else self.default_rtt

        self.version_mismatch = self._check_versions()
        try:
            # Version mismatches emit sklearn warnings; we surface our own instead.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.edge_model = joblib.load(os.path.join(models_dir, "edge_model.pkl"))
                self.cloud_model = joblib.load(os.path.join(models_dir, "cloud_model.pkl"))
            self.models_loaded = True
        except FileNotFoundError:
            self.models_loaded = False

    def _check_versions(self) -> bool:
        import sklearn
        trained = self.metadata.get("versions", {}).get("scikit-learn")
        if trained and trained != sklearn.__version__:
            log.warning("models trained with scikit-learn %s but %s is installed; "
                        "re-run train_model.py", trained, sklearn.__version__)
            return True
        return False

    def predict(self, features: dict, code_bytes: int = 0, rtt_s: float | None = None,
                cloud_load: dict | None = None, edge_load: dict | None = None) -> dict:
        if "error" in features or not self.models_loaded:
            return {"predicted_edge_time": 0.0, "predicted_cloud_time": 0.0,
                    "routing_decision": "EDGE", "confidence": 0.0, "method": "fallback"}

        x = np.array([[features.get(c, 0.0) for c in self.feature_cols]], dtype=float)
        edge_s = max(10 ** float(self.edge_model.predict(x)[0]) - EPS, 1e-4)
        cloud_s = max(10 ** float(self.cloud_model.predict(x)[0]) - EPS, 1e-4)

        rtt = self.fixed_rtt if self.fixed_rtt is not None else (rtt_s if rtt_s is not None else self.default_rtt)
        transfer = code_bytes / self.bandwidth if self.bandwidth else 0.0
        edge_total = edge_s + queue_penalty(edge_load, edge_s)
        cloud_total = cloud_s + rtt + transfer + queue_penalty(cloud_load, cloud_s)

        cloud_wins = cloud_total < edge_total * (1.0 - self.margin)
        d = math.log(edge_total) - math.log(cloud_total)  # > 0: cloud faster
        sd = LN10 * math.hypot(self.sigma_edge, self.sigma_cloud * cloud_s / cloud_total)
        p_cloud = _phi(d / sd) if sd > 0 else (1.0 if d > 0 else 0.0)
        return {
            "predicted_edge_time": round(edge_total, 4),
            "predicted_cloud_time": round(cloud_total, 4),
            "predicted_edge_compute": round(edge_s, 4),
            "predicted_cloud_compute": round(cloud_s, 4),
            "rtt_s": round(rtt, 4),
            "transfer_s": round(transfer, 4),
            "routing_decision": "CLOUD" if cloud_wins else "EDGE",
            "confidence": round(p_cloud if cloud_wins else 1.0 - p_cloud, 4),
            "method": "regression",
        }
