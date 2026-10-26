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
    ap.add_argument("--bootstrap", type=int, default=0, help="resamples for confidence intervals (0 = off)")
    ap.add_argument("--markdown", default="", help="also write a markdown summary here")
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
    rel = 100 * (t["scheduler"] / t["always_edge"] - 1)
    print(f"scheduler vs always-edge: {rel:+.1f}%   vs oracle: {100*(t['scheduler']/t['oracle']-1):+.1f}%")

    # Where the gain comes from: seconds saved/lost per script relative to always-edge.
    chosen = np.where(choose, cloud + rtt, edge)
    delta = edge - chosen  # > 0: scheduler saved time on this script
    order = np.argsort(-np.abs(delta))
    top = order[:10]
    saved, lost = delta[delta > 0].sum(), -delta[delta < 0].sum()
    print(f"time saved on {int((delta > 0).sum())} scripts: {saved:.1f}s; lost on {int((delta < 0).sum())}: {lost:.1f}s; "
          f"top-10 scripts account for {100*np.abs(delta[top]).sum()/np.abs(delta).sum():.0f}% of the movement")
    ci = None
    if a.bootstrap:
        rng = np.random.default_rng(0)
        def ratio(idx):
            return 100 * (chosen[idx].sum() / edge[idx].sum() - 1)
        n = len(df)
        by_script = [ratio(rng.integers(0, n, n)) for _ in range(a.bootstrap)]
        fam = df.family.to_numpy()
        groups = {f: np.where(fam == f)[0] for f in np.unique(fam)}
        keys = list(groups)
        by_family = []
        for _ in range(a.bootstrap):
            pick = rng.choice(len(keys), len(keys))
            by_family.append(ratio(np.concatenate([groups[keys[i]] for i in pick])))
        ci = {"script": np.percentile(by_script, [2.5, 97.5]), "family": np.percentile(by_family, [2.5, 97.5])}
        print(f"95% bootstrap CI for scheduler vs always-edge: resampling scripts [{ci['script'][0]:+.1f}%, "
              f"{ci['script'][1]:+.1f}%]; resampling families [{ci['family'][0]:+.1f}%, {ci['family'][1]:+.1f}%] "
              f"({a.bootstrap} resamples)")
    if a.markdown:
        lines = ["# Asymmetric two-worker experiment", "",
                 f"{len(df)} scripts, {df.family.nunique()} families, simulated RTT {a.rtt_ms:.0f} ms, "
                 f"{folds}-fold grouped out-of-fold predictions.", "",
                 "| Policy | Total (s) | vs always-edge |", "| --- | ---: | ---: |"]
        for k in ("oracle", "always_edge", "scheduler", "always_cloud"):
            lines.append(f"| {k.replace('_', ' ')} | {t[k]:.1f} | {100*(t[k]/t['always_edge']-1):+.1f}% |")
        lines += ["", f"* Cloud faster than edge incl. RTT on {wins}/{len(df)} scripts; scheduler routed {int(choose.sum())} to cloud.",
                  f"* Time saved on {int((delta > 0).sum())} scripts: {saved:.1f}s; lost on {int((delta < 0).sum())}: {lost:.1f}s.",
                  f"* R2 (log10, families held out): edge {r2_score(np.log10(edge+EPS), oe):.3f}, "
                  f"cloud {r2_score(np.log10(cloud+EPS), oc):.3f}."]
        if ci:
            lines.append(f"* 95% bootstrap CI vs always-edge: scripts [{ci['script'][0]:+.1f}%, {ci['script'][1]:+.1f}%], "
                         f"families [{ci['family'][0]:+.1f}%, {ci['family'][1]:+.1f}%].")
        lines += ["", "Both workers ran on one machine (CPU limits differ); the network delay is simulated. "
                  "This is not an EC2 measurement."]
        with open(a.markdown, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
