import joblib
import numpy as np
import os

class LatencyPredictor:
    def __init__(self, network_latency_cloud_ms: float = 80.0):
        self.network_latency_cloud = network_latency_cloud_ms / 1000.0
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_dir = os.path.join(base_dir, "models")
        
        try:
            self.scaler = joblib.load(os.path.join(models_dir, "scaler.pkl"))
            self.edge_model = joblib.load(os.path.join(models_dir, "edge_rf_model.pkl"))
            self.cloud_model = joblib.load(os.path.join(models_dir, "cloud_rf_model.pkl"))
            self.models_loaded = True
        except FileNotFoundError:
            self.models_loaded = False

    def predict(self, features: dict) -> dict:
        if "error" in features or not self.models_loaded:
            return {"predicted_edge_time": 0.0, "predicted_cloud_time": 0.0}

        X_input = np.array([[
            features.get("num_lines", 1),
            features.get("num_loops", 0),
            features.get("max_loop_depth", 0),
            features.get("num_operations", 0),
            features.get("has_heavy_lib", 0),
            features.get("num_function_calls", 0),
            features.get("num_comprehensions", 0),
            features.get("max_integer", 0),
            features.get("estimated_complexity", 0)
        ]])

        X_scaled = self.scaler.transform(X_input)

        # Get the Log-10 predictions
        edge_pred_log = self.edge_model.predict(X_scaled)[0]
        cloud_pred_log = self.cloud_model.predict(X_scaled)[0]

        # Reverse the Log-10 transformation to get actual seconds (subtract the 1e-6 offset)
        edge_pred_sec = (10 ** edge_pred_log) - 1e-6
        cloud_pred_sec = (10 ** cloud_pred_log) - 1e-6

        # Add physical network RTT to the cloud prediction
        final_cloud_pred = cloud_pred_sec + self.network_latency_cloud

        return {
            "predicted_edge_time": round(float(max(0.0001, edge_pred_sec)), 4),
            "predicted_cloud_time": round(float(max(0.0001, final_cloud_pred)), 4)
        }