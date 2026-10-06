"""
Improved training pipeline:
  1. Trains edge & cloud REGRESSORS for latency display.
  2. Trains a binary CLASSIFIER that directly predicts the routing decision.
  3. Prints cross-validated accuracy, confusion matrix, and feature importance.
  4. Auto-measures and stores the real network RTT to the cloud worker.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os
import time
import json

# ── 0. Configuration ─────────────────────────────────────────────────────────
CLOUD_WORKER_URL = "http://18.60.146.38:8000/execute"
RTT_PROBE_COUNT = 7
MODELS_DIR = "models"
DATA_FILE = "hardware_benchmark.csv"

# ── 1. Auto-Measure Real RTT ─────────────────────────────────────────────────
print("=" * 60)
print("Step 1: Measuring real network RTT to cloud worker...")
print("=" * 60)

rtt_samples = []
try:
    import requests
    for i in range(RTT_PROBE_COUNT):
        start = time.perf_counter()
        resp = requests.post(CLOUD_WORKER_URL, json={"code": "pass"}, timeout=10)
        elapsed = time.perf_counter() - start
        if resp.status_code == 200:
            # Subtract the server-side compute time to get pure network RTT
            server_time = resp.json().get("execution_time_seconds", 0)
            net_rtt = elapsed - server_time
            rtt_samples.append(net_rtt)
            print(f"  Probe {i+1}: total={elapsed*1000:.1f}ms, "
                  f"server={server_time*1000:.1f}ms, net_rtt={net_rtt*1000:.1f}ms")
except Exception as e:
    print(f"  Warning: Could not reach cloud worker: {e}")
    print("  Using default RTT of 150ms")

if rtt_samples:
    # Use the median to be robust against outliers
    measured_rtt = float(np.median(rtt_samples))
    print(f"\n  Measured RTT (median): {measured_rtt*1000:.1f}ms")
else:
    measured_rtt = 0.150

# ── 2. Load Data ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Step 2: Loading benchmark data...")
print("=" * 60)

df = pd.read_csv(DATA_FILE)
print(f"  Dataset: {len(df)} samples, {len(df.columns)} columns")

FEATURE_COLS = [
    'num_lines', 'num_loops', 'max_loop_depth', 'num_operations',
    'has_heavy_lib', 'num_function_calls', 'num_comprehensions',
    'max_integer', 'estimated_complexity'
]

X = df[FEATURE_COLS]

# Realistic Edge Device Modeling:
# Simple tasks (low complexity, no loops, no heavy libs) execute with 1.0x factor (instant on edge).
# Heavy tasks scale up proportionally with computational complexity and loop depth.
complexity_excess = np.maximum(0, df['estimated_complexity'] - 2.5)
edge_scale = 1.0 + 2.0 * df['has_heavy_lib'] + 0.6 * complexity_excess + 0.4 * df['num_loops']
df['modeled_edge_time'] = df['actual_edge_time'] * edge_scale

# Regression targets (log-scaled)
y_edge_log = np.log10(df['modeled_edge_time'] + 1e-6)
y_cloud_log = np.log10(df['actual_cloud_time'] + 1e-6)

# Classification target: should we offload to cloud?
# CLOUD label = 1 when cloud_compute + RTT < edge_compute
y_decision = (df['actual_cloud_time'] + measured_rtt < df['modeled_edge_time']).astype(int)
cloud_count = y_decision.sum()
edge_count = len(y_decision) - cloud_count
print(f"  Edge Model: Complexity-Aware Edge Scale (1.0x base, up to 9x for heavy compute)")
print(f"  Class balance: CLOUD={cloud_count} ({100*cloud_count/len(df):.1f}%), "
      f"EDGE={edge_count} ({100*edge_count/len(df):.1f}%)")

# ── 3. Scale Features ────────────────────────────────────────────────────────
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ── 4. Train Regressors ──────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Step 3: Training latency regression models...")
print("=" * 60)

edge_model = HistGradientBoostingRegressor(
    max_iter=500, learning_rate=0.05, max_depth=6,
    min_samples_leaf=5, l2_regularization=0.1, random_state=42
)
cloud_model = HistGradientBoostingRegressor(
    max_iter=500, learning_rate=0.05, max_depth=6,
    min_samples_leaf=5, l2_regularization=0.1, random_state=42
)

# Cross-validate regressors
edge_r2 = cross_val_score(edge_model, X_scaled, y_edge_log, cv=5, scoring='r2')
cloud_r2 = cross_val_score(cloud_model, X_scaled, y_cloud_log, cv=5, scoring='r2')
print(f"  Edge regressor R²:  {edge_r2.mean():.4f} ± {edge_r2.std():.4f}")
print(f"  Cloud regressor R²: {cloud_r2.mean():.4f} ± {cloud_r2.std():.4f}")

# Fit on full data
edge_model.fit(X_scaled, y_edge_log)
cloud_model.fit(X_scaled, y_cloud_log)

# ── 5. Train Binary Classifier ───────────────────────────────────────────────
print("\n" + "=" * 60)
print("Step 4: Training binary routing classifier...")
print("=" * 60)

if cloud_count >= 5:
    # Enough CLOUD samples to train a meaningful classifier
    classifier = HistGradientBoostingClassifier(
        max_iter=500, learning_rate=0.05, max_depth=6,
        min_samples_leaf=5, l2_regularization=0.1,
        class_weight={0: 1.0, 1: max(1.0, edge_count / max(cloud_count, 1))},
        random_state=42
    )
    
    # Stratified cross-validation
    if cloud_count >= 5:
        cv = StratifiedKFold(n_splits=min(5, cloud_count), shuffle=True, random_state=42)
        clf_acc = cross_val_score(classifier, X_scaled, y_decision, cv=cv, scoring='accuracy')
        print(f"  Classifier accuracy: {clf_acc.mean():.4f} ± {clf_acc.std():.4f}")
    
    # Fit on full data
    classifier.fit(X_scaled, y_decision)
    
    # Full-data evaluation
    y_pred = classifier.predict(X_scaled)
    print(f"\n  Classification Report (on training data):")
    labels = ['EDGE', 'CLOUD']
    print(classification_report(y_decision, y_pred, target_names=labels, zero_division=0))
    
    cm = confusion_matrix(y_decision, y_pred)
    print(f"  Confusion Matrix:")
    print(f"                  Predicted EDGE  Predicted CLOUD")
    print(f"    Actual EDGE:  {cm[0][0]:>14d}  {cm[0][1]:>15d}")
    if len(cm) > 1:
        print(f"    Actual CLOUD: {cm[1][0]:>14d}  {cm[1][1]:>15d}")
    
    classifier_trained = True
else:
    print(f"  WARNING: Only {cloud_count} CLOUD samples — too few for a classifier.")
    print(f"  The model will fall back to regression-based comparison.")
    classifier = None
    classifier_trained = False

# ── 6. Feature Importance ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Step 5: Feature importance analysis...")
print("=" * 60)

# Use permutation importance for edge model
from sklearn.inspection import permutation_importance
perm_imp = permutation_importance(edge_model, X_scaled, y_edge_log, 
                                   n_repeats=10, random_state=42)
print(f"\n  {'Feature':25s}  {'Importance':>12s}")
print(f"  {'-'*25}  {'-'*12}")
sorted_idx = perm_imp.importances_mean.argsort()[::-1]
for idx in sorted_idx:
    print(f"  {FEATURE_COLS[idx]:25s}  {perm_imp.importances_mean[idx]:12.4f}")

# ── 7. Save Everything ───────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Step 6: Saving models and metadata...")
print("=" * 60)

os.makedirs(MODELS_DIR, exist_ok=True)
joblib.dump(scaler, os.path.join(MODELS_DIR, "scaler.pkl"))
joblib.dump(edge_model, os.path.join(MODELS_DIR, "edge_rf_model.pkl"))
joblib.dump(cloud_model, os.path.join(MODELS_DIR, "cloud_rf_model.pkl"))

if classifier_trained:
    joblib.dump(classifier, os.path.join(MODELS_DIR, "routing_classifier.pkl"))
    print("  ✓ Saved routing_classifier.pkl")

# Save metadata (RTT, feature order, class balance, edge factor)
metadata = {
    "measured_rtt_seconds": measured_rtt,
    "measured_rtt_ms": round(measured_rtt * 1000, 1),
    "edge_device_modeling": "adaptive (2.5x base, 5.0x heavy lib)",
    "feature_columns": FEATURE_COLS,
    "training_samples": len(df),
    "cloud_samples": int(cloud_count),
    "edge_samples": int(edge_count),
    "classifier_trained": classifier_trained,
    "edge_r2_mean": round(float(edge_r2.mean()), 4),
    "cloud_r2_mean": round(float(cloud_r2.mean()), 4),
}
with open(os.path.join(MODELS_DIR, "training_metadata.json"), "w") as f:
    json.dump(metadata, f, indent=2)

print("  ✓ Saved scaler.pkl, edge_rf_model.pkl, cloud_rf_model.pkl")
print("  ✓ Saved training_metadata.json")
print(f"\n{'=' * 60}")
print(f"Training complete! RTT={measured_rtt*1000:.0f}ms, "
      f"Samples={len(df)}, CLOUD={cloud_count}, EDGE={edge_count}")
print(f"{'=' * 60}")