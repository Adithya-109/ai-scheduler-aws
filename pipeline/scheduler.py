from pipeline.feature_extractor import CodeFeatureExtractor
from pipeline.predictor import LatencyPredictor

class OffloadingScheduler:
    def __init__(self, cloud_rtt_ms: float = None):
        self.extractor = CodeFeatureExtractor()
        self.predictor = LatencyPredictor(network_latency_cloud_ms=cloud_rtt_ms)

    def schedule(self, code_str: str) -> dict:
        # 1. Extract features
        features = self.extractor.analyze(code_str)
        if "error" in features:
            return {"error": features["error"]}

        # 2. Predict times and get routing decision
        predictions = self.predictor.predict(features)
        
        # The decision now comes from the classifier (or regression fallback)
        decision = predictions["routing_decision"]
        confidence = predictions["confidence"]
        method = predictions["method"]

        return {
            "features": features,
            "predictions": predictions,
            "decision": decision,
            "confidence": confidence,
            "decision_method": method
        }