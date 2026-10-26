"""Train the edge/cloud latency regressors on MEASURED timings only.

    python3 train_model.py                    # use stored RTT from models/training_metadata.json
    python3 train_model.py --probe            # measure RTT live against CLOUD_WORKER_URL
    python3 train_model.py --rtt-ms 95        # set RTT explicitly
    python3 train_model.py --log logs/decisions.jsonl   # add logged outcomes (bandit feedback)
    python3 train_model.py --data data/docker_asym_v1/asym_benchmark.csv --out-dir models/asym --rtt-ms 110

There is no synthetic label. The routing decision is a rule applied at
inference time:  CLOUD  iff  predicted_cloud + RTT + transfer < predicted_edge.
Evaluation uses out-of-fold predictions with whole script families held out,
and reports the total wall-clock time of each policy on real measurements, so
"is the scheduler better than always running locally?" is answered directly.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import time
import warnings

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold

import config
from pipeline.dataset import (
    DATA_FILE,
    ROOT,
    file_sha256,
    load_benchmark,
    load_decision_log,
    policy_totals,
)
from pipeline.feature_extractor import FEATURE_COLUMNS, FEATURE_VERSION

MODELS_DIR = os.path.join(ROOT, "models")
META_PATH = os.path.join(MODELS_DIR, "training_metadata.json")
DEFAULT_RTT_S = 0.110
EPS = 1e-6


def make_regressor() -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.06, max_depth=5, min_samples_leaf=5,
        l2_regularization=0.1, early_stopping=True, validation_fraction=0.15,
        n_iter_no_change=20, random_state=42,
    )


def measure_rtt(url: str, probes: int = 9) -> float | None:
    """Median network RTT (request time minus server-side time) to a worker."""
    import requests

    samples = []
    for _ in range(probes):
        t0 = time.perf_counter()
        try:
            r = requests.post(url, json={"code": "pass"}, headers=config.auth_headers(), timeout=10)
        except requests.RequestException as e:
            print(f"  probe failed: {e}")
            continue
        elapsed = time.perf_counter() - t0
        if r.status_code == 200:
            samples.append(elapsed - r.json().get("execution_time_seconds", 0.0))
    return statistics.median(samples) if samples else None


def resolve_rtt(args, meta_path: str = META_PATH) -> tuple[float, str]:
    if args.rtt_ms is not None:
        return args.rtt_ms / 1000.0, "cli"
    if args.probe:
        url = config.execute_url(config.CLOUD_WORKER_URL)
        if not url:
            raise SystemExit("--probe needs CLOUD_WORKER_URL (see .env.example)")
        rtt = measure_rtt(url)
        if rtt is None:
            raise SystemExit("could not measure RTT: cloud worker unreachable")
        return rtt, "probe"
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as fh:
            prev = json.load(fh)
        if "measured_rtt_seconds" in prev:
            return float(prev["measured_rtt_seconds"]), "previous_metadata"
    return DEFAULT_RTT_S, "default"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtt-ms", type=float)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--log", default="", help="decision log (JSONL) to learn from")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--data", default=DATA_FILE, help="benchmark CSV (file, actual_edge_time, actual_cloud_time)")
    ap.add_argument("--out-dir", default=MODELS_DIR, help="where to write the models and metadata")
    args = ap.parse_args()
    out_dir = os.path.abspath(args.out_dir)
    meta_path = os.path.join(out_dir, "training_metadata.json")
    warnings.filterwarnings("ignore", category=UserWarning)

    rtt, rtt_source = resolve_rtt(args, meta_path)
    print(f"RTT = {rtt*1000:.1f} ms ({rtt_source})")

    df = load_benchmark(args.data)
    print(f"dataset: {len(df)} scripts, {df.family.nunique()} families, features v{FEATURE_VERSION}")
    X = df[FEATURE_COLUMNS].to_numpy(dtype=float)
    edge = df.actual_edge_time.to_numpy()
    cloud = df.actual_cloud_time.to_numpy()
    y_edge, y_cloud = np.log10(edge + EPS), np.log10(cloud + EPS)

    real_cloud_wins = int((cloud + rtt < edge).sum())
    print(f"measured cloud wins (compute + RTT < edge): {real_cloud_wins} / {len(df)}")

    # ---- out-of-fold evaluation, whole families held out ----
    oof_e, oof_c = np.zeros(len(df)), np.zeros(len(df))
    for tr, te in GroupKFold(n_splits=args.folds).split(X, groups=df.family):
        oof_e[te] = make_regressor().fit(X[tr], y_edge[tr]).predict(X[te])
        oof_c[te] = make_regressor().fit(X[tr], y_cloud[tr]).predict(X[te])
    pe, pc = 10 ** oof_e - EPS, 10 ** oof_c - EPS
    choose_cloud = pc + rtt < pe
    totals = policy_totals(edge, cloud, rtt, choose_cloud)
    metrics = {
        "edge_r2_log_grouped": float(r2_score(y_edge, oof_e)),
        "cloud_r2_log_grouped": float(r2_score(y_cloud, oof_c)),
        "edge_median_abs_pct_error": float(np.median(np.abs(pe - edge) / edge)),
        "cloud_median_abs_pct_error": float(np.median(np.abs(pc - cloud) / cloud)),
        "sigma_edge_log10": float(np.std(y_edge - oof_e)),
        "sigma_cloud_log10": float(np.std(y_cloud - oof_c)),
        "policy_total_seconds": totals,
        "scheduler_vs_always_edge_pct": 100 * (totals["scheduler"] / totals["always_edge"] - 1),
        "scheduler_regret_vs_oracle_pct": 100 * (totals["scheduler"] / totals["oracle"] - 1),
        "routed_to_cloud": int(choose_cloud.sum()),
        "measured_cloud_wins": real_cloud_wins,
    }
    for k in ("edge_r2_log_grouped", "cloud_r2_log_grouped", "edge_median_abs_pct_error",
              "cloud_median_abs_pct_error", "scheduler_vs_always_edge_pct", "scheduler_regret_vs_oracle_pct"):
        print(f"  {k:34s} {metrics[k]:.4f}")
    print("  policy totals (s):", {k: round(v, 1) for k, v in totals.items()})

    # ---- final fit: benchmark + logged outcomes ----
    Xe, ye, Xc, yc = X, y_edge, X, y_cloud
    logged = load_decision_log(args.log)
    n_logged = {"edge": 0, "cloud": 0}
    if len(logged):
        for side in ("edge", "cloud"):
            sub = logged[logged.target == side]
            if len(sub):
                Xs = sub[FEATURE_COLUMNS].to_numpy(dtype=float)
                ys = np.log10(sub.compute_time_s.to_numpy() + EPS)
                if side == "edge":
                    Xe, ye = np.vstack([Xe, Xs]), np.concatenate([ye, ys])
                else:
                    Xc, yc = np.vstack([Xc, Xs]), np.concatenate([yc, ys])
                n_logged[side] = len(sub)
        print(f"  + logged outcomes: {n_logged}")
    edge_model = make_regressor().fit(Xe, ye)
    cloud_model = make_regressor().fit(Xc, yc)

    os.makedirs(out_dir, exist_ok=True)
    joblib.dump(edge_model, os.path.join(out_dir, "edge_model.pkl"))
    joblib.dump(cloud_model, os.path.join(out_dir, "cloud_model.pkl"))
    hw = {}
    sidecar = os.path.splitext(args.data)[0] + ".meta.json"
    if os.path.exists(sidecar):
        with open(sidecar, encoding="utf-8") as fh:
            m = json.load(fh)
        hw = {"edge": m.get("edge", {}).get("description"), "cloud": m.get("cloud", {}).get("instance_type")}
    meta = {
        "model_type": "HistGradientBoostingRegressor (log10 seconds)",
        "feature_version": FEATURE_VERSION,
        "feature_columns": FEATURE_COLUMNS,
        "measured_rtt_seconds": rtt,
        "measured_rtt_ms": round(rtt * 1000, 1),
        "rtt_source": rtt_source,
        "sigma_edge_log10": metrics["sigma_edge_log10"],
        "sigma_cloud_log10": metrics["sigma_cloud_log10"],
        "training_samples": len(df),
        "logged_samples": n_logged,
        "families": sorted(df.family.unique().tolist()),
        "data_file": os.path.relpath(os.path.abspath(args.data), ROOT),
        "data_sha256": file_sha256(args.data),
        "hardware": hw,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "versions": {"scikit-learn": sklearn.__version__, "numpy": np.__version__,
                     "python": platform.python_version()},
        "cv": {"scheme": f"GroupKFold({args.folds}) by script family, out-of-fold", **metrics},
    }
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(f"saved edge_model.pkl, cloud_model.pkl, training_metadata.json to {out_dir}")


if __name__ == "__main__":
    main()
