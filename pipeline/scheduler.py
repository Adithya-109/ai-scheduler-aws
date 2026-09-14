from pipeline.feature_extractor import CodeFeatureExtractor
from pipeline.predictor import LatencyPredictor

class OffloadingScheduler:
    def __init__(self, cloud_rtt_ms: float = 80.0):
        self.extractor = CodeFeatureExtractor()
        self.predictor = LatencyPredictor(network_latency_cloud_ms=cloud_rtt_ms)

    def schedule(self, code_str: str) -> dict:
        # 1. Extract features
        features = self.extractor.analyze(code_str)
        if "error" in features:
            return {"error": features["error"]}

        # 2. Predict times
        predictions = self.predictor.predict(features)
        
        edge_t = predictions["predicted_edge_time"]
        cloud_t = predictions["predicted_cloud_time"]

        # 3. Make the decision: Pick the smallest time!
        decision = "EDGE" if edge_t <= cloud_t else "CLOUD"

        return {
            "features": features,
            "predictions": predictions,
            "decision": decision
        }