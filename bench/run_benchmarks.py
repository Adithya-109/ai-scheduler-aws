"""
Benchmarks for ai-scheduler-aws.  python3 bench/run_benchmarks.py
Writes bench/results.json.
"""
import json, os, sys, time, statistics, subprocess, warnings, types
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedKFold, GroupKFold, cross_val_score, cross_val_predict
from pipeline.feature_extractor import CodeFeatureExtractor
from pipeline.scheduler import OffloadingScheduler

R = {}
F = ['num_lines','num_loops','max_loop_depth','num_operations','has_heavy_lib',
     'num_function_calls','num_comprehensions','max_integer','estimated_complexity']
files = sorted(f for f in os.listdir("test_scripts") if f.endswith(".py"))
codes = [open(os.path.join("test_scripts", f)).read() for f in files]

def pct(xs, p): return float(np.percentile(xs, p))

# ── B1. AST feature extraction latency (README claims < 12 ms) ─────────────
ex = CodeFeatureExtractor(); lat = []
for _ in range(5):
    for c in codes:
        t = time.perf_counter(); ex.analyze(c); lat.append((time.perf_counter()-t)*1e3)
R["B1_extract_ms"] = dict(n=len(lat), p50=pct(lat,50), p95=pct(lat,95), p99=pct(lat,99), max=max(lat))

# ── B2. End-to-end schedule() latency (extract + scale + 2 regressors + clf) ─
s = OffloadingScheduler(); lat = []
for c in codes[:200]: s.schedule(c)  # warm
for c in codes:
    t = time.perf_counter(); s.schedule(c); lat.append((time.perf_counter()-t)*1e3)
R["B2_schedule_ms"] = dict(p50=pct(lat,50), p95=pct(lat,95), max=max(lat),
                           throughput_per_s=1000/statistics.mean(lat))
t = time.perf_counter(); OffloadingScheduler(); R["B2_cold_load_ms"] = (time.perf_counter()-t)*1e3

# ── B3. Dataset reality check ──────────────────────────────────────────────
df = pd.read_csv("hardware_benchmark.csv")
meta = json.load(open("models/training_metadata.json"))
rtt = meta["measured_rtt_seconds"]
complexity_excess = np.maximum(0, df.estimated_complexity - 2.5)
edge_scale = 1.0 + 2.0*df.has_heavy_lib + 0.6*complexity_excess + 0.4*df.num_loops
df["modeled_edge"] = df.actual_edge_time * edge_scale
y_model = (df.actual_cloud_time + rtt < df.modeled_edge).astype(int)
y_real = (df.actual_cloud_time + rtt < df.actual_edge_time).astype(int)
y_real_norrt = (df.actual_cloud_time < df.actual_edge_time).astype(int)
R["B3_dataset"] = dict(
    rows=len(df), rtt_ms=rtt*1000,
    cloud_labels_training=int(y_model.sum()),
    cloud_labels_real_measurements=int(y_real.sum()),
    cloud_faster_even_ignoring_rtt=int(y_real_norrt.sum()),
    median_cloud_over_edge_ratio=float((df.actual_cloud_time/df.actual_edge_time).median()),
    edge_scale_min=float(edge_scale.min()), edge_scale_max=float(edge_scale.max()),
    edge_scale_median=float(edge_scale.median()),
    unique_feature_vectors=int(df.groupby(F).ngroups),
)

# ── B4. Honest model evaluation ───────────────────────────────────────────
X = df[F].values
# Script family groups (map rows to files via unique feature vectors where possible)
fx = pd.DataFrame([ex.analyze(c) for c in codes]); fx["file"] = files
fx["fam"] = fx.file.str.replace(r"_[0-9].*", "", regex=True)
key = lambda d: d[F].astype(float).round(6).astype(str).agg("|".join, axis=1)
fx["k"] = key(fx); df["k"] = key(df)
fam = df.k.map(fx.drop_duplicates("k").set_index("k").fam).fillna("unk")
# exact feature-vector groups — prevents identical vectors leaking across folds
groups = df.k.astype("category").cat.codes

def clf(): return HistGradientBoostingClassifier(max_iter=500, learning_rate=0.05, max_depth=6,
        min_samples_leaf=5, l2_regularization=0.1, random_state=42)
skf = StratifiedKFold(5, shuffle=True, random_state=42)

acc_skf = cross_val_score(make_pipeline(StandardScaler(), clf()), X, y_model, cv=skf).mean()
acc_grp = cross_val_score(make_pipeline(StandardScaler(), clf()), X, y_model, cv=GroupKFold(5), groups=groups).mean()

# How much of the label is a closed-form function of the features?
# Label = cloud+rtt < edge*scale(features). Fit a tiny logistic model on 3 features.
lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
acc_lr3 = cross_val_score(lr, df[["estimated_complexity","has_heavy_lib","num_loops"]].values, y_model, cv=skf).mean()
acc_always_edge = 1 - y_model.mean()
# single-threshold rule on edge_scale (which is pure feature arithmetic)
best_thr = max(((edge_scale > t).astype(int) == y_model).mean() for t in np.unique(edge_scale))

R["B4_classifier"] = dict(
    readme_claim=0.994,
    shipped_label_stratified_cv=float(acc_skf),
    shipped_label_group_cv=float(acc_grp),
    baseline_always_edge=float(acc_always_edge),
    baseline_logreg_3_features=float(acc_lr3),
    baseline_single_threshold_on_feature_formula=float(best_thr),
    accuracy_vs_REAL_labels_if_always_edge=float(1 - y_real.mean()),
)

# Shipped model scored against real measurements
sch = OffloadingScheduler()
pred_cloud = []
for _, r in df.iterrows():
    p = sch.predictor.predict({c: r[c] for c in F}); pred_cloud.append(p["routing_decision"] == "CLOUD")
pred_cloud = np.array(pred_cloud)
R["B4_shipped_model"] = dict(
    routes_to_cloud=int(pred_cloud.sum()),
    accuracy_vs_training_labels=float((pred_cloud == y_model.values).mean()),
    accuracy_vs_real_labels=float((pred_cloud == y_real.values).mean()),
)

# ── B5. Regret: wall-clock under each policy using REAL measured times ──────
edge = df.actual_edge_time.values; cloud = df.actual_cloud_time.values + rtt
oracle = np.minimum(edge, cloud)
R["B5_total_seconds_real"] = dict(
    oracle=float(oracle.sum()), always_edge=float(edge.sum()), always_cloud=float(cloud.sum()),
    shipped_scheduler=float(np.where(pred_cloud, cloud, edge).sum()),
)
R["B5_total_seconds_real"]["shipped_slowdown_vs_always_edge_pct"] = \
    100*(R["B5_total_seconds_real"]["shipped_scheduler"]/R["B5_total_seconds_real"]["always_edge"]-1)

# ── B6. Regressor quality: random vs group split; prediction error in seconds ─
def reg(): return HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05, max_depth=6,
        min_samples_leaf=5, l2_regularization=0.1, random_state=42)
ye = np.log10(df.modeled_edge + 1e-6); yc = np.log10(df.actual_cloud_time + 1e-6)
from sklearn.model_selection import KFold
r2 = lambda y, cv, g=None: float(cross_val_score(make_pipeline(StandardScaler(), reg()), X, y, cv=cv, groups=g, scoring="r2").mean())
pc = 10**cross_val_predict(make_pipeline(StandardScaler(), reg()), X, yc, cv=GroupKFold(5), groups=groups)
mape = np.median(np.abs(pc - df.actual_cloud_time)/df.actual_cloud_time)
R["B6_regressors"] = dict(
    readme_r2=0.972, metadata_edge_r2=meta["edge_r2_mean"], metadata_cloud_r2=meta["cloud_r2_mean"],
    edge_r2_kfold_unshuffled=r2(ye, 5), cloud_r2_kfold_unshuffled=r2(yc, 5),
    edge_r2_shuffled=r2(ye, KFold(5, shuffle=True, random_state=0)),
    cloud_r2_shuffled=r2(yc, KFold(5, shuffle=True, random_state=0)),
    cloud_r2_group=r2(yc, GroupKFold(5), groups),
    cloud_median_abs_pct_error_group=float(mape),
)

# ── B7. RTT sensitivity of the shipped scheduler ───────────────────────────
sweep = {}
for ms in (1, 10, 50, 110, 200, 500):
    sc = OffloadingScheduler(cloud_rtt_ms=ms)
    res = [sc.schedule(c) for c in codes]
    res = [r for r in res if "error" not in r]
    sweep[ms] = dict(
        cloud_pct=100*np.mean([r["decision"] == "CLOUD" for r in res]),
        regressor_says_cloud_pct=100*np.mean([r["predictions"]["predicted_cloud_time"] < r["predictions"]["predicted_edge_time"] for r in res]),
        low_confidence_decisions=int(sum(r["confidence"] < 0.5 for r in res)),
    )
R["B7_rtt_sweep"] = sweep

# ── B8. Worker execution overhead (subprocess spawn per job) ───────────────
lat = []
for _ in range(30):
    t = time.perf_counter(); subprocess.run([sys.executable, "-c", "pass"], capture_output=True)
    lat.append((time.perf_counter()-t)*1e3)
lat_np = []
for _ in range(10):
    t = time.perf_counter(); subprocess.run([sys.executable, "-c", "import numpy"], capture_output=True)
    lat_np.append((time.perf_counter()-t)*1e3)
R["B8_worker_spawn_ms"] = dict(python_pass_p50=pct(lat,50), import_numpy_p50=pct(lat_np,50),
    share_of_dataset_edge_median_pct=100*pct(lat,50)/1000/df.actual_edge_time.median())

json.dump(R, open("bench/results.json", "w"), indent=2, default=float)
print(json.dumps(R, indent=2, default=lambda x: round(float(x), 4)))
