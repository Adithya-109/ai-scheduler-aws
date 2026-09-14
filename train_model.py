import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os

print("Loading empirical hardware data...")
df = pd.read_csv("hardware_benchmark.csv")

# 9 Features
X = df[['num_lines', 'num_loops', 'max_loop_depth', 'num_operations', 
        'has_heavy_lib', 'num_function_calls', 'num_comprehensions', 
        'max_integer', 'estimated_complexity']]

# Log-transform the target variables (add 1e-6 to prevent log(0) errors)
y_edge_log = np.log10(df['actual_edge_time'] + 1e-6)
y_cloud_log = np.log10(df['actual_cloud_time'] + 1e-6)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

print("Training Gradient Boosting Models on Log-Scaled Latencies...")
# Increased max_depth to allow the model to learn complex feature interactions
edge_model = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_depth=8, random_state=42)
edge_model.fit(X_scaled, y_edge_log)

cloud_model = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_depth=8, random_state=42)
cloud_model.fit(X_scaled, y_cloud_log)

os.makedirs("models", exist_ok=True)
joblib.dump(scaler, "models/scaler.pkl")
joblib.dump(edge_model, "models/edge_rf_model.pkl")  
joblib.dump(cloud_model, "models/cloud_rf_model.pkl")

print("Log-Scaled Gradient Boosting models trained successfully!")