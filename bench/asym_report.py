"""Score the scheduler on a freshly collected two-worker dataset (read-only:
no models or committed data are overwritten).

    python3 bench/asym_report.py experiments/<ts>/asym_benchmark.csv --rtt-ms 110
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings

import numpy as np
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.dataset import load_benchmark, policy_totals  # noqa: E402
from pipeline.feature_extractor import FEATURE_COLUMNS  # noqa: E402
from train_model import EPS, make_regressor  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--rtt-ms", type=float, default=110.0)
    ap.add_argument("--folds", type=int, default=5)
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    rtt = a.rtt_ms / 1000.0
    df = load_benchmark(a.csv)
    X = df[FEATURE_COLUMNS].to_numpy(float)
    edge, cloud = df.actual_edge_time.to_numpy(), df.actual_cloud_time.to_numpy()
    folds = max(2, min(a.folds, df.family.nunique()))
    oe, oc = np.zeros(len(df)), np.zeros(len(df))
    for tr, te in GroupKFold(n_splits=folds).split(X, groups=df.family):
        oe[te] = make_regressor().fit(X[tr], np.log10(edge[tr] + EPS)).predict(X[te])
        oc[te] = make_regressor().fit(X[tr], np.log10(cloud[tr] + EPS)).predict(X[te])
    pe, pc = 10 ** oe - EPS, 10 ** oc - EPS
    choose = pc + rtt < pe
    t = policy_totals(edge, cloud, rtt, choose)
    wins = int((cloud + rtt < edge).sum())
    print(f"scripts={len(df)} families={df.family.nunique()} folds={folds} simulated RTT={a.rtt_ms:.0f} ms")
    print(f"median edge/cloud compute: {np.median(edge):.3f}s / {np.median(cloud):.3f}s")
    print(f"measured cloud wins (cloud + RTT < edge): {wins}/{len(df)}; routed to cloud: {int(choose.sum())}")
    print(f"R2 log10 (held-out families): edge {r2_score(np.log10(edge+EPS), oe):.3f}, "
          f"cloud {r2_score(np.log10(cloud+EPS), oc):.3f}")
    print("policy totals (s): " + ", ".join(f"{k}={v:.1f}" for k, v in t.items()))
    print(f"scheduler vs always-edge: {100*(t['scheduler']/t['always_edge']-1):+.1f}%   "
          f"vs oracle: {100*(t['scheduler']/t['oracle']-1):+.1f}%")


if __name__ == "__main__":
    main()
