import hashlib
import time

from pipeline.feature_extractor import FEATURE_VERSION, CodeFeatureExtractor
from pipeline.predictor import LatencyPredictor


class OffloadingScheduler:
    """Extract features, predict both latencies, apply the routing rule.

    RTT precedence: an explicit ``cloud_rtt_ms`` (e.g. the UI slider) wins,
    then a live ``rtt_tracker`` estimate, then the value measured at training.
    """

    def __init__(self, cloud_rtt_ms: float = None, rtt_tracker=None, margin: float = 0.0,
                 bandwidth_bytes_per_s: float = None, history=None):
        self.extractor = CodeFeatureExtractor()
        self.predictor = LatencyPredictor(network_latency_cloud_ms=cloud_rtt_ms, margin=margin,
                                          bandwidth_bytes_per_s=bandwidth_bytes_per_s)
        self.rtt_tracker = rtt_tracker
        self.history = history

    def schedule(self, code_str: str, cloud_load: dict = None, edge_load: dict = None) -> dict:
        t0 = time.perf_counter()
        features = self.extractor.analyze(code_str)
        if "error" in features:
            return {"error": features["error"]}

        code_hash = hashlib.sha256(code_str.encode("utf-8", "replace")).hexdigest()[:16]
        h = self.history
        live_rtt = self.rtt_tracker.value if self.rtt_tracker is not None else None
        predictions = self.predictor.predict(
            features, code_bytes=len(code_str.encode("utf-8", "replace")), rtt_s=live_rtt,
            cloud_load=cloud_load, edge_load=edge_load,
            observed_edge_s=h.median(code_hash, "edge") if h else None,
            observed_cloud_s=h.median(code_hash, "cloud") if h else None)

        return {
            "features": features,
            "feature_version": FEATURE_VERSION,
            "predictions": predictions,
            "decision": predictions["routing_decision"],
            "confidence": predictions["confidence"],
            "decision_method": predictions["method"],
            "code_hash": code_hash,
            "scheduling_ms": round((time.perf_counter() - t0) * 1000, 3),
        }
