import joblib
import numpy as np
import pandas as pd
import os
import json

class LatencyPredictor:
    def __init__(self, network_latency_cloud_ms: float = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_dir = os.path.join(base_dir, "models")
        
        # Load training metadata (contains measured RTT)
        metadata_path = os.path.join(models_dir, "training_metadata.json")
        self.metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                self.metadata = json.load(f)

        # Default feature columns
        self.feature_cols = self.metadata.get("feature_columns", [
            "num_lines", "num_loops", "max_loop_depth", "num_operations",
            "has_heavy_lib", "num_function_calls", "num_comprehensions",
            "max_integer", "estimated_complexity"
        ])

        # Use measured RTT from training if user didn't override
        if network_latency_cloud_ms is not None:
            self.network_latency_cloud = network_latency_cloud_ms / 1000.0
        else:
            self.network_latency_cloud = self.metadata.get("measured_rtt_seconds", 0.121)
        
        try:
            self.scaler = joblib.load(os.path.join(models_dir, "scaler.pkl"))
            self.edge_model = joblib.load(os.path.join(models_dir, "edge_rf_model.pkl"))
            self.cloud_model = joblib.load(os.path.join(models_dir, "cloud_rf_model.pkl"))
            self.models_loaded = True
        except FileNotFoundError:
            self.models_loaded = False

        # Load binary classifier if available
        classifier_path = os.path.join(models_dir, "routing_classifier.pkl")
        try:
            self.classifier = joblib.load(classifier_path)
            self.classifier_loaded = True
        except FileNotFoundError:
            self.classifier = None
            self.classifier_loaded = False

    def predict(self, features: dict) -> dict:
        if "error" in features or not self.models_loaded:
            return {
                "predicted_edge_time": 0.0,
                "predicted_cloud_time": 0.0,
                "routing_decision": "EDGE",
                "confidence": 0.0,
                "method": "fallback"
            }

        input_dict = {col: [features.get(col, 0)] for col in self.feature_cols}
        X_df = pd.DataFrame(input_dict)
        X_scaled = self.scaler.transform(X_df)

        # ── Regression: Predict latencies for display ──
        edge_pred_log = self.edge_model.predict(X_scaled)[0]
        cloud_pred_log = self.cloud_model.predict(X_scaled)[0]

        edge_pred_sec = (10 ** edge_pred_log) - 1e-6
        cloud_pred_sec = (10 ** cloud_pred_log) - 1e-6

        # Add network RTT to cloud prediction
        final_cloud_pred = cloud_pred_sec + self.network_latency_cloud

        # ── Harmonized Routing Decision ──
        # Principle: If Edge is faster than Cloud compute + Network RTT, always route to Edge.
        # Otherwise, if Cloud saves more time than the network delay, confirm with classifier.
        if edge_pred_sec <= final_cloud_pred:
            decision = "EDGE"
            if self.classifier_loaded and self.classifier is not None:
                probabilities = self.classifier.predict_proba(X_scaled)[0]
                confidence = float(probabilities[0]) # probability of EDGE
                method = "classifier"
            else:
                confidence = min(1.0, (final_cloud_pred - edge_pred_sec) / max(final_cloud_pred, 1e-4))
                method = "regression"
        else:
            # Cloud + RTT is faster than Edge compute
            if self.classifier_loaded and self.classifier is not None:
                decision_label = self.classifier.predict(X_scaled)[0]
                probabilities = self.classifier.predict_proba(X_scaled)[0]
                decision = "CLOUD" if decision_label == 1 else "EDGE"
                confidence = float(max(probabilities))
                method = "classifier"
            else:
                decision = "CLOUD"
                confidence = min(1.0, (edge_pred_sec - final_cloud_pred) / max(edge_pred_sec, 1e-4))
                method = "regression"

        return {
            "predicted_edge_time": round(float(max(0.0001, edge_pred_sec)), 4),
            "predicted_cloud_time": round(float(max(0.0001, final_cloud_pred)), 4),
            "routing_decision": decision,
            "confidence": round(confidence, 4),
            "method": method
        }