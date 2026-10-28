"""Comparative evaluation for the paper: AI scheduler vs edge-only, cloud-only,
random and a static-threshold heuristic, on every measured dataset.

    python3 bench/paper_eval.py                 # writes bench/paper/{REPORT.md, results.json, tables/, figures/}
    python3 bench/paper_eval.py --bootstrap 500 # fewer resamples (faster)

Read-only: no model or dataset is written. Every policy is scored on MEASURED
edge and cloud times; the scheduler and the heuristic only ever see predictions
made with the script's whole family held out (grouped K-fold), so no score
comes from a script the model was trained on. Needs matplotlib for figures.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
from scipy import stats
from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from pipeline.dataset import DATA_FILE, load_benchmark  # noqa: E402
from pipeline.feature_extractor import FEATURE_COLUMNS  # noqa: E402
from train_model import EPS, make_regressor  # noqa: E402

OUT = os.path.join(ROOT, "bench", "paper")
DATASETS = [  # key, label, csv, rtt seconds, description
    ("similar_hw", "Similar hardware", DATA_FILE, 0.1097,
     "legacy edge vs EC2, near-identical CPUs, measured RTT"),
    ("asym_v1", "Asymmetric (591)", os.path.join(ROOT, "data", "docker_asym_v1", "asym_benchmark.csv"), 0.110,
     "Docker edge --cpus=0.5 vs cloud --cpus=4, simulated 110 ms RTT"),
    ("asym_v2", "Asymmetric + heavy (633)", os.path.join(ROOT, "data", "docker_asym_v2", "asym_benchmark.csv"), 0.110,
     "asym_v1 plus 42 heavy NumPy/BLAS/FFT workloads"),
]
POLICIES = ["edge_only", "cloud_only", "random", "heuristic", "scheduler", "oracle"]
LABEL = {"edge_only": "Edge-only", "cloud_only": "Cloud-only", "random": "Random (p=0.5)",
         "heuristic": "Static threshold", "scheduler": "AI Scheduler", "oracle": "Oracle (bound)"}
TIE_BAND = 0.10  # |edge - cloud_total| / max(.) below this is a near-tie: either choice costs < 10%


# --------------------------------------------------------------------------- predictions

def oof_predictions(df, splitter):
    """Out-of-fold log10 predictions with whole families held out, plus the
    static-threshold heuristic's out-of-fold choice (threshold tuned on the
    training folds only)."""
    X = df[FEATURE_COLUMNS].to_numpy(float)
    e, c = df.actual_edge_time.to_numpy(), df.actual_cloud_time.to_numpy()
    ye, yc = np.log10(e + EPS), np.log10(c + EPS)
    oe, oc = np.zeros(len(df)), np.zeros(len(df))
    for tr, te in splitter.split(X, groups=df.family):
        oe[te] = make_regressor().fit(X[tr], ye[tr]).predict(X[te])
        oc[te] = make_regressor().fit(X[tr], yc[tr]).predict(X[te])
    return 10 ** oe - EPS, 10 ** oc - EPS


def heuristic_choice(df, rtt, splitter):
    """Offload iff the static cost estimate exceeds a threshold tau. tau is the
    value that minimises total measured time on the training folds."""
    cx = df.estimated_complexity.to_numpy(float)
    e, c = df.actual_edge_time.to_numpy(), df.actual_cloud_time.to_numpy() + rtt
    out = np.zeros(len(df), bool)
    for tr, te in splitter.split(cx, groups=df.family):
        cands = np.concatenate([[np.inf], np.unique(cx[tr])])
        cost = [np.where(cx[tr] >= t, c[tr], e[tr]).sum() for t in cands]
        tau = cands[int(np.argmin(cost))]
        out[te] = cx[te] >= tau
    return out


# --------------------------------------------------------------------------- metrics

def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (mid - half, mid + half)


def latency_stats(t):
    return {"total_s": float(t.sum()), "mean_s": float(t.mean()), "median_s": float(np.median(t)),
            "p95_s": float(np.percentile(t, 95)), "p99_s": float(np.percentile(t, 99)), "max_s": float(t.max())}


def classification(real, pred):
    tn, fp, fn, tp = confusion_matrix(real, pred, labels=[False, True]).ravel()
    n = len(real)
    acc = (tp + tn) / n
    zero = {"zero_division": 0}
    return {
        "n": int(n), "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "accuracy": float(acc), "accuracy_ci95": [float(x) for x in wilson(tp + tn, n)],
        "balanced_accuracy": float(balanced_accuracy_score(real, pred)) if real.any() and (~real).any() else float("nan"),
        "precision_cloud": float(precision_score(real, pred, **zero)),
        "recall_cloud": float(recall_score(real, pred, **zero)),
        "f1_cloud": float(f1_score(real, pred, **zero)),
        "mcc": float(matthews_corrcoef(real, pred)) if real.any() and (~real).any() else float("nan"),
        "majority_class_accuracy": float(max(real.mean(), 1 - real.mean())),
    }


def regression(actual, pred):
    la, lp = np.log10(actual + EPS), np.log10(pred + EPS)
    ape = np.abs(pred - actual) / actual
    ratio = np.maximum(pred / actual, actual / np.maximum(pred, EPS))
    return {"r2_log10": float(r2_score(la, lp)), "mae_log10": float(np.mean(np.abs(la - lp))),
            "rmse_log10": float(np.sqrt(np.mean((la - lp) ** 2))),
            "median_ape": float(np.median(ape)), "mean_ape": float(np.mean(ape)),
            "within_25pct": float(np.mean(ape <= 0.25)), "within_2x": float(np.mean(ratio <= 2)),
            "spearman": float(stats.spearmanr(actual, pred).statistic),
            "pearson_log10": float(stats.pearsonr(la, lp).statistic)}


def bootstrap_ratio(chosen, base, groups, B, rng):
    """95% CI of 100*(sum(chosen)/sum(base) - 1), resampling scripts and, separately, whole families."""
    n = len(chosen)
    by_script = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        by_script.append(100 * (chosen[i].sum() / base[i].sum() - 1))
    keys = np.unique(groups)
    idx = {k: np.where(groups == k)[0] for k in keys}
    by_family = []
    for _ in range(B):
        i = np.concatenate([idx[keys[j]] for j in rng.integers(0, len(keys), len(keys))])
        by_family.append(100 * (chosen[i].sum() / base[i].sum() - 1))
    return {"script": [float(x) for x in np.percentile(by_script, [2.5, 97.5])],
            "family": [float(x) for x in np.percentile(by_family, [2.5, 97.5])],
            "samples_script": by_script}


def paired_test(a, b):
    """Wilcoxon signed-rank on per-job latency, a vs b (two-sided), with rank-biserial effect size."""
    d = a - b
    nz = d[np.abs(d) > 1e-12]
    if len(nz) < 10:
        return {"n_nonzero": int(len(nz)), "p_value": float("nan"), "rank_biserial": float("nan")}
    w = stats.wilcoxon(nz)
    r = stats.rankdata(np.abs(nz))
    rb = (r[nz > 0].sum() - r[nz < 0].sum()) / r.sum()
    return {"n_nonzero": int(len(nz)), "p_value": float(w.pvalue), "rank_biserial": float(rb),
            "wins": int((nz < 0).sum()), "losses": int((nz > 0).sum())}


# --------------------------------------------------------------------------- per-dataset run

def evaluate(key, label, csv, rtt, desc, B, rng):
    t0 = time.perf_counter()
    df = load_benchmark(csv)
    e, c = df.actual_edge_time.to_numpy(), df.actual_cloud_time.to_numpy()
    ct = c + rtt
    fam = df.family.to_numpy()
    k = max(2, min(5, df.family.nunique()))
    gkf = GroupKFold(n_splits=k)
    pe, pc = oof_predictions(df, gkf)
    choose = {
        "edge_only": np.zeros(len(df), bool),
        "cloud_only": np.ones(len(df), bool),
        "heuristic": heuristic_choice(df, rtt, gkf),
        "scheduler": pc + rtt < pe,
        "oracle": ct < e,
    }
    real = choose["oracle"]
    lat = {p: np.where(ch, ct, e) for p, ch in choose.items()}
    # Random: expectation over 1000 coin-flip assignments; percentiles from the pooled draws.
    flips = rng.random((1000, len(df))) < 0.5
    rnd = np.where(flips, ct, e)
    oracle_total = lat["oracle"].sum()

    pol = {}
    for p in POLICIES:
        if p == "random":
            s = {"total_s": float(rnd.sum(1).mean()), "total_sd_s": float(rnd.sum(1).std()),
                 "mean_s": float(rnd.mean()), "median_s": float(np.median(rnd)),
                 "p95_s": float(np.percentile(rnd, 95)), "p99_s": float(np.percentile(rnd, 99)),
                 "max_s": float(rnd.max()), "routed_to_cloud": float(flips.sum(1).mean()),
                 "decision_accuracy": float((flips == real).mean())}
        else:
            s = latency_stats(lat[p])
            s["routed_to_cloud"] = int(choose[p].sum())
            s["decision_accuracy"] = float((choose[p] == real).mean())
        s["vs_edge_only_pct"] = 100 * (s["total_s"] / e.sum() - 1)
        s["vs_cloud_only_pct"] = 100 * (s["total_s"] / ct.sum() - 1)
        s["regret_vs_oracle_pct"] = 100 * (s["total_s"] / oracle_total - 1)
        s["oracle_efficiency_pct"] = 100 * oracle_total / s["total_s"]
        pol[p] = s

    gap = np.abs(e - ct) / np.maximum(e, ct)
    decisive = gap >= TIE_BAND
    sched, heur = choose["scheduler"], choose["heuristic"]
    misrouted = sched != real
    cost_of_errors = np.abs(e - ct)[misrouted]

    boot = {b: bootstrap_ratio(lat["scheduler"], base, fam, B, rng)
            for b, base in (("edge_only", e), ("cloud_only", ct))}
    boot["heuristic"] = bootstrap_ratio(lat["scheduler"], lat["heuristic"], fam, B, rng)

    # Stricter split: leave ONE family out (every family becomes the test set once).
    pe1, pc1 = oof_predictions(df, LeaveOneGroupOut())
    s1 = np.where(pc1 + rtt < pe1, ct, e)

    per_family = []
    for f in np.unique(fam):
        m = fam == f
        per_family.append({"family": str(f), "n": int(m.sum()), "edge_only_s": float(e[m].sum()),
                           "cloud_only_s": float(ct[m].sum()), "scheduler_s": float(lat["scheduler"][m].sum()),
                           "oracle_s": float(lat["oracle"][m].sum()),
                           "accuracy": float((sched[m] == real[m]).mean())})

    sweep = []
    for ms in (0, 5, 10, 25, 50, 75, 110, 150, 200, 300, 500):
        r = ms / 1000
        ct_r = c + r
        sweep.append({"rtt_ms": ms, "edge_only_s": float(e.sum()), "cloud_only_s": float(ct_r.sum()),
                      "scheduler_s": float(np.where(pc + r < pe, ct_r, e).sum()),
                      "oracle_s": float(np.minimum(e, ct_r).sum()),
                      "accuracy": float(((pc + r < pe) == (ct_r < e)).mean()),
                      "cloud_share_pct": float(100 * (pc + r < pe).mean())})

    return {
        "key": key, "label": label, "description": desc, "rtt_ms": rtt * 1000,
        "scripts": len(df), "families": int(df.family.nunique()), "folds": k,
        "median_edge_s": float(np.median(e)), "median_cloud_s": float(np.median(c)),
        "median_cloud_over_edge": float(np.median(c / e)),
        "cloud_wins": int(real.sum()), "decisive_scripts": int(decisive.sum()),
        "policies": pol,
        "classification": {
            "scheduler": classification(real, sched),
            "scheduler_decisive_only": classification(real[decisive], sched[decisive]),
            "heuristic": classification(real, heur),
        },
        "misroute_cost": {"n": int(misrouted.sum()), "total_s": float(cost_of_errors.sum()),
                          "median_s": float(np.median(cost_of_errors)) if len(cost_of_errors) else 0.0,
                          "share_of_edge_total_pct": float(100 * cost_of_errors.sum() / e.sum())},
        "regression": {"edge": regression(e, pe), "cloud": regression(c, pc)},
        "bootstrap": {k_: {kk: v for kk, v in b.items() if kk != "samples_script"} for k_, b in boot.items()},
        "significance": {"vs_edge_only": paired_test(lat["scheduler"], e),
                         "vs_cloud_only": paired_test(lat["scheduler"], ct),
                         "vs_heuristic": paired_test(lat["scheduler"], lat["heuristic"])},
        "leave_one_family_out": {"scheduler_s": float(s1.sum()),
                                 "vs_edge_only_pct": float(100 * (s1.sum() / e.sum() - 1)),
                                 "accuracy": float(((pc1 + rtt < pe1) == real).mean()),
                                 "edge_r2_log10": regression(e, pe1)["r2_log10"],
                                 "cloud_r2_log10": regression(c, pc1)["r2_log10"]},
        "per_family": per_family, "rtt_sweep": sweep, "seconds_to_run": time.perf_counter() - t0,
        "_arrays": {"e": e, "c": c, "ct": ct, "pe": pe, "pc": pc, "lat": lat, "rnd": rnd[0],
                    "real": real, "sched": sched, "fam": fam,
                    "boot_edge": np.array(boot["edge_only"]["samples_script"])},
    }


def decision_overhead(n=200):
    from pipeline.scheduler import OffloadingScheduler
    files = sorted(f for f in os.listdir(os.path.join(ROOT, "test_scripts")) if f.endswith(".py"))[:n]
    codes = [open(os.path.join(ROOT, "test_scripts", f), encoding="utf-8").read() for f in files]
    s = OffloadingScheduler()
    for code in codes[:20]:
        s.schedule(code)
    lat = []
    for code in codes:
        t = time.perf_counter()
        s.schedule(code)
        lat.append((time.perf_counter() - t) * 1e3)
    return {"n": len(lat), "p50_ms": float(np.percentile(lat, 50)), "p95_ms": float(np.percentile(lat, 95)),
            "mean_ms": float(np.mean(lat))}


# --------------------------------------------------------------------------- tables

def fmt_ci(ci):
    return f"[{ci[0]:+.1f}, {ci[1]:+.1f}]"


def write_tables(R, tdir):
    os.makedirs(tdir, exist_ok=True)
    md = {}
    # T1: policy comparison
    rows = ["| Dataset | Policy | Total (s) | Mean (s) | p95 (s) | vs Edge-only | vs Cloud-only | Regret vs oracle | "
            "Routed to cloud | Decision acc. |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    csv = ["dataset,policy,total_s,mean_s,median_s,p95_s,p99_s,vs_edge_only_pct,vs_cloud_only_pct,"
           "regret_vs_oracle_pct,routed_to_cloud,decision_accuracy"]
    tex = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
           r"Dataset & Policy & Total (s) & p95 (s) & vs Edge & vs Cloud & Regret & Acc. \\", r"\midrule"]
    for d in R["datasets"]:
        for p in POLICIES:
            s = d["policies"][p]
            name = f"**{LABEL[p]}**" if p == "scheduler" else LABEL[p]
            rows.append(f"| {d['label']} | {name} | {s['total_s']:.1f} | {s['mean_s']:.3f} | {s['p95_s']:.3f} | "
                        f"{s['vs_edge_only_pct']:+.1f}% | {s['vs_cloud_only_pct']:+.1f}% | "
                        f"{s['regret_vs_oracle_pct']:+.1f}% | {s['routed_to_cloud']:.0f} | "
                        f"{100*s['decision_accuracy']:.1f}% |")
            csv.append(f"{d['key']},{p},{s['total_s']:.4f},{s['mean_s']:.5f},{s['median_s']:.5f},{s['p95_s']:.5f},"
                       f"{s['p99_s']:.5f},{s['vs_edge_only_pct']:.3f},{s['vs_cloud_only_pct']:.3f},"
                       f"{s['regret_vs_oracle_pct']:.3f},{s['routed_to_cloud']:.1f},{s['decision_accuracy']:.4f}")
            nm = rf"\textbf{{{LABEL[p]}}}" if p == "scheduler" else LABEL[p]
            tex.append(f"{d['label'] if p == POLICIES[0] else ''} & {nm} & {s['total_s']:.1f} & {s['p95_s']:.3f} & "
                       f"{s['vs_edge_only_pct']:+.1f}\\% & {s['vs_cloud_only_pct']:+.1f}\\% & "
                       f"{s['regret_vs_oracle_pct']:+.1f}\\% & {100*s['decision_accuracy']:.1f}\\% \\\\")
        tex.append(r"\midrule")
    tex[-1] = r"\bottomrule"
    tex.append(r"\end{tabular}")
    md["policies"] = rows
    _save(tdir, "table1_policies", rows, csv, tex)

    # T2: routing accuracy (classification of 'cloud is faster')
    rows = ["| Dataset | Subset | n | Accuracy (95% CI) | Majority baseline | Balanced acc. | Precision | Recall | F1 | MCC | TP/FP/FN/TN |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    csv = ["dataset,subset,n,accuracy,acc_lo,acc_hi,majority,balanced_accuracy,precision,recall,f1,mcc,tp,fp,fn,tn"]
    tex = [r"\begin{tabular}{llrrrrrrr}", r"\toprule",
           r"Dataset & Subset & $n$ & Acc. & Majority & Bal. acc. & Prec. & Rec. & MCC \\", r"\midrule"]
    for d in R["datasets"]:
        for sub, nm in (("scheduler", "AI Scheduler, all"), ("scheduler_decisive_only", "AI Scheduler, decisive"),
                        ("heuristic", "Static threshold, all")):
            m = d["classification"][sub]
            rows.append(f"| {d['label']} | {nm} | {m['n']} | {100*m['accuracy']:.1f}% "
                        f"({100*m['accuracy_ci95'][0]:.1f}–{100*m['accuracy_ci95'][1]:.1f}) | "
                        f"{100*m['majority_class_accuracy']:.1f}% | {_pct(m['balanced_accuracy'])} | "
                        f"{100*m['precision_cloud']:.1f}% | {100*m['recall_cloud']:.1f}% | {m['f1_cloud']:.3f} | "
                        f"{_num(m['mcc'])} | {m['tp']}/{m['fp']}/{m['fn']}/{m['tn']} |")
            csv.append(f"{d['key']},{sub},{m['n']},{m['accuracy']:.4f},{m['accuracy_ci95'][0]:.4f},"
                       f"{m['accuracy_ci95'][1]:.4f},{m['majority_class_accuracy']:.4f},{m['balanced_accuracy']:.4f},"
                       f"{m['precision_cloud']:.4f},{m['recall_cloud']:.4f},{m['f1_cloud']:.4f},{m['mcc']:.4f},"
                       f"{m['tp']},{m['fp']},{m['fn']},{m['tn']}")
            tex.append(f"{d['label'] if sub == 'scheduler' else ''} & {nm} & {m['n']} & {100*m['accuracy']:.1f}\\% & "
                       f"{100*m['majority_class_accuracy']:.1f}\\% & {_pct(m['balanced_accuracy'], tex=True)} & "
                       f"{100*m['precision_cloud']:.1f}\\% & {100*m['recall_cloud']:.1f}\\% & {_num(m['mcc'])} \\\\")
        tex.append(r"\midrule")
    tex[-1] = r"\bottomrule"
    tex.append(r"\end{tabular}")
    md["classification"] = rows
    _save(tdir, "table2_routing_accuracy", rows, csv, tex)

    # T3: latency-prediction accuracy
    rows = ["| Dataset | Node | R² (log10) | MAE (log10) | Median APE | Within ±25% | Within 2× | Spearman ρ |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    csv = ["dataset,node,r2_log10,mae_log10,rmse_log10,median_ape,mean_ape,within_25pct,within_2x,spearman,pearson_log10"]
    tex = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
           r"Dataset & Node & $R^2$ & MAE$_{\log}$ & MdAPE & $\pm$25\% & $2\times$ & $\rho$ \\", r"\midrule"]
    for d in R["datasets"]:
        for node in ("edge", "cloud"):
            g = d["regression"][node]
            rows.append(f"| {d['label']} | {node} | {g['r2_log10']:.3f} | {g['mae_log10']:.3f} | "
                        f"{100*g['median_ape']:.1f}% | {100*g['within_25pct']:.1f}% | {100*g['within_2x']:.1f}% | "
                        f"{g['spearman']:.3f} |")
            csv.append(f"{d['key']},{node},{g['r2_log10']:.4f},{g['mae_log10']:.4f},{g['rmse_log10']:.4f},"
                       f"{g['median_ape']:.4f},{g['mean_ape']:.4f},{g['within_25pct']:.4f},{g['within_2x']:.4f},"
                       f"{g['spearman']:.4f},{g['pearson_log10']:.4f}")
            tex.append(f"{d['label'] if node == 'edge' else ''} & {node} & {g['r2_log10']:.3f} & {g['mae_log10']:.3f} & "
                       f"{100*g['median_ape']:.1f}\\% & {100*g['within_25pct']:.1f}\\% & {100*g['within_2x']:.1f}\\% & "
                       f"{g['spearman']:.3f} \\\\")
        tex.append(r"\midrule")
    tex[-1] = r"\bottomrule"
    tex.append(r"\end{tabular}")
    md["regression"] = rows
    _save(tdir, "table3_latency_prediction", rows, csv, tex)

    # T4: statistical significance and robustness
    rows = ["| Dataset | Comparison | Δ total (95% CI, scripts) | 95% CI, families | Wilcoxon p | Rank-biserial r | Jobs faster / slower |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    csv = ["dataset,comparison,delta_pct,ci_script_lo,ci_script_hi,ci_family_lo,ci_family_hi,p_value,rank_biserial,wins,losses"]
    for d in R["datasets"]:
        for b, nm, sig in (("edge_only", "AI Scheduler vs Edge-only", "vs_edge_only"),
                           ("cloud_only", "AI Scheduler vs Cloud-only", "vs_cloud_only"),
                           ("heuristic", "AI Scheduler vs Static threshold", "vs_heuristic")):
            bt, st = d["bootstrap"][b], d["significance"][sig]
            delta = 100 * (d["policies"]["scheduler"]["total_s"] / d["policies"][b]["total_s"] - 1)
            rows.append(f"| {d['label']} | {nm} | {delta:+.1f}% {fmt_ci(bt['script'])} | {fmt_ci(bt['family'])} | "
                        f"{_p(st['p_value'])} | {_num(st['rank_biserial'])} | "
                        f"{st.get('wins', 0)} / {st.get('losses', 0)} |")
            csv.append(f"{d['key']},{b},{delta:.3f},{bt['script'][0]:.3f},{bt['script'][1]:.3f},"
                       f"{bt['family'][0]:.3f},{bt['family'][1]:.3f},{st['p_value']:.3g},{st['rank_biserial']:.4f},"
                       f"{st.get('wins', 0)},{st.get('losses', 0)}")
    md["significance"] = rows
    _save(tdir, "table4_significance", rows, csv, None)

    # T5: dataset summary + robustness
    rows = ["| Dataset | Scripts | Families | RTT | Median edge / cloud (s) | Cloud wins | 5-fold vs edge | Leave-one-family-out vs edge | LOFO accuracy |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for d in R["datasets"]:
        lo = d["leave_one_family_out"]
        rows.append(f"| {d['label']} | {d['scripts']} | {d['families']} | {d['rtt_ms']:.0f} ms | "
                    f"{d['median_edge_s']:.3f} / {d['median_cloud_s']:.3f} | {d['cloud_wins']} | "
                    f"{d['policies']['scheduler']['vs_edge_only_pct']:+.1f}% | {lo['vs_edge_only_pct']:+.1f}% | "
                    f"{100*lo['accuracy']:.1f}% |")
    md["datasets"] = rows
    _save(tdir, "table5_datasets_robustness", rows, None, None)
    return md


def _pct(x, tex=False):
    return "n/a" if x != x else (f"{100*x:.1f}\\%" if tex else f"{100*x:.1f}%")


def _num(x):
    return "n/a" if x != x else f"{x:.3f}"


def _p(p):
    return "n/a" if p != p else ("< 1e-10" if p < 1e-10 else f"{p:.2g}")


def _save(tdir, name, md_rows, csv_rows, tex_rows):
    with open(os.path.join(tdir, name + ".md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md_rows) + "\n")
    if csv_rows:
        with open(os.path.join(tdir, name + ".csv"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(csv_rows) + "\n")
    if tex_rows:
        with open(os.path.join(tdir, name + ".tex"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(tex_rows) + "\n")


# --------------------------------------------------------------------------- figures

def write_figures(R, fdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    os.makedirs(fdir, exist_ok=True)
    # Reference palette (validated light-mode categorical slots, fixed order) and chart ink.
    COL = {"scheduler": "#2a78d6", "edge_only": "#eb6834", "cloud_only": "#1baf7a",
           "heuristic": "#eda100", "random": "#e87ba4", "oracle": "#898781"}
    INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 9, "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
        "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF,
        "savefig.facecolor": SURF, "legend.frameon": False, "legend.fontsize": 8, "lines.linewidth": 2,
        "savefig.dpi": 300, "savefig.bbox": "tight",
    })
    ds = R["datasets"]

    def save(fig, name):
        fig.savefig(os.path.join(fdir, name + ".png"))
        fig.savefig(os.path.join(fdir, name + ".pdf"))
        plt.close(fig)

    # Fig 1: total wall-clock per policy, one panel per dataset (each on its own seconds axis).
    order = ["oracle", "scheduler", "heuristic", "edge_only", "random", "cloud_only"]
    fig, axes = plt.subplots(1, len(ds), figsize=(11, 3.2), sharey=True)
    for ax, d in zip(axes, ds):
        vals = [d["policies"][p]["total_s"] for p in order]
        y = np.arange(len(order))
        ax.barh(y, vals, height=0.62, color=[COL[p] for p in order], edgecolor=SURF, linewidth=2)
        ax.set_yticks(y, [LABEL[p] for p in order])
        ax.invert_yaxis()
        ax.grid(axis="y", visible=False)
        for yi, p, v in zip(y, order, vals):
            rel = d["policies"][p]["vs_edge_only_pct"]
            tag = "baseline" if p == "edge_only" else f"{rel + 0.0:+.1f}%".replace("-0.0", "0.0").replace("+0.0", "0.0")
            ax.text(v + max(vals) * 0.015, yi, f"{v:.0f} s  ({tag})", va="center", fontsize=7.5, color=INK2)
        ax.set_xlim(0, max(vals) * 1.42)
        ax.set_title(d["label"])
        ax.set_xlabel("Total wall-clock time (s)")
    fig.suptitle("Total completion time of every job, by routing policy (lower is better)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK, y=1.03)
    fig.tight_layout()
    save(fig, "fig1_policy_total_time")

    # Fig 2: improvement vs each baseline with 95% bootstrap CI (forest plot).
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    comps = [("edge_only", "vs Edge-only"), ("cloud_only", "vs Cloud-only"), ("heuristic", "vs Static threshold")]
    ccol = {"edge_only": COL["edge_only"], "cloud_only": COL["cloud_only"], "heuristic": COL["heuristic"]}
    yt, yl, yy = [], [], 0
    for d in ds:
        for b, nm in comps:
            delta = 100 * (d["policies"]["scheduler"]["total_s"] / d["policies"][b]["total_s"] - 1)
            lo, hi = d["bootstrap"][b]["script"]
            ax.plot([lo, hi], [yy, yy], color=ccol[b], lw=2, solid_capstyle="round")
            ax.plot(delta, yy, "o", ms=8, color=ccol[b], mec=SURF, mew=2)
            ax.text(max(hi, delta) + 2, yy, f"{delta:+.1f}%  [{lo:+.1f}, {hi:+.1f}]", va="center", fontsize=7.5,
                    color=INK2)
            yt.append(yy)
            yl.append(f"{d['label']}  {nm}")
            yy += 1
        yy += 0.6
    ax.axvline(0, color=AXIS, lw=1)
    ax.set_yticks(yt, yl, fontsize=7.5)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Change in total time from using the AI Scheduler (%) — negative is faster")
    lo_all = min(d["bootstrap"][b]["script"][0] for d in ds for b, _ in comps)
    hi_all = max(d["bootstrap"][b]["script"][1] for d in ds for b, _ in comps)
    ax.set_xlim(lo_all - 5, hi_all + 40)
    ax.set_title("AI Scheduler vs each baseline, with 95% bootstrap confidence intervals")
    save(fig, "fig2_improvement_ci")

    # Fig 3: per-job latency CDF (asymmetric datasets).
    asym = [d for d in ds if d["key"] != "similar_hw"]
    fig, axes = plt.subplots(1, len(asym), figsize=(10, 3.4), sharey=True)
    styles = {"scheduler": "-", "edge_only": "--", "cloud_only": "-.", "heuristic": (0, (5, 1.5)),
              "random": ":", "oracle": (0, (1, 1))}
    for ax, d in zip(np.atleast_1d(axes), asym):
        A = d["_arrays"]
        for p in ["edge_only", "cloud_only", "random", "heuristic", "scheduler", "oracle"]:
            t = np.sort(A["rnd"] if p == "random" else A["lat"][p])
            ax.plot(t, np.arange(1, len(t) + 1) / len(t), ls=styles[p], color=COL[p],
                    lw=2.4 if p == "scheduler" else 1.6, label=LABEL[p])
        ax.set_xscale("log")
        ax.set_xlabel("Per-job completion time (s, log scale)")
        ax.set_title(d["label"])
        ax.set_ylim(0, 1.01)
    np.atleast_1d(axes)[0].set_ylabel("Fraction of jobs finished")
    np.atleast_1d(axes)[-1].legend(loc="lower right")
    fig.suptitle("Distribution of per-job completion time", x=0.01, ha="left", fontsize=11, fontweight="bold",
                 color=INK, y=1.02)
    fig.tight_layout()
    save(fig, "fig3_latency_cdf")

    # Fig 4: confusion matrices of the routing decision.
    cmap = LinearSegmentedColormap.from_list("seq", ["#f0efec", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
    fig, axes = plt.subplots(1, len(ds), figsize=(10, 3.1))
    for ax, d in zip(axes, ds):
        m = d["classification"]["scheduler"]
        M = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]])
        frac = M / np.maximum(M.sum(1, keepdims=True), 1)  # row-normalised: share of each true class
        ax.imshow(frac, cmap=cmap, vmin=0, vmax=1)
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{M[i, j]}\n({100*frac[i, j]:.0f}% of row)", ha="center", va="center", fontsize=8.5,
                        color="#ffffff" if frac[i, j] > 0.5 else INK)
        ax.set_xticks([0, 1], ["Edge", "Cloud"])
        ax.set_yticks([0, 1], ["Edge", "Cloud"])
        ax.set_xlabel("Scheduler chose")
        ax.set_ylabel("Actually faster")
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(f"{d['label']}\nacc {100*m['accuracy']:.1f}%, MCC {_num(m['mcc'])}", fontsize=9)
    fig.suptitle("Routing decisions vs the measured faster node", x=0.01, ha="left", fontsize=11,
                 fontweight="bold", color=INK, y=1.04)
    fig.tight_layout()
    save(fig, "fig4_confusion_matrices")

    # Fig 5: predicted vs measured latency (every dataset, both nodes).
    fig, axes = plt.subplots(2, len(ds), figsize=(10, 6.2))
    for j, d in enumerate(ds):
        A = d["_arrays"]
        for i, (node, act, pr, col) in enumerate((("Edge", A["e"], A["pe"], COL["edge_only"]),
                                                   ("Cloud", A["c"], A["pc"], COL["cloud_only"]))):
            ax = axes[i, j]
            ax.scatter(act, np.maximum(pr, 1e-4), s=9, color=col, alpha=0.55, edgecolors="none")
            lo = max(1e-4, min(act.min(), pr[pr > 0].min()))
            hi = max(act.max(), pr.max())
            ax.plot([lo, hi], [lo, hi], color=INK2, lw=1)
            ax.fill_between([lo, hi], [lo / 2, hi / 2], [lo * 2, hi * 2], color=MUTED, alpha=0.12, lw=0)
            ax.set_xscale("log")
            ax.set_yscale("log")
            g = d["regression"][node.lower()]
            ax.text(0.04, 0.95, f"R² {g['r2_log10']:.3f}\nwithin 2×: {100*g['within_2x']:.0f}%",
                    transform=ax.transAxes, va="top", fontsize=7.5, color=INK2)
            ax.set_title(f"{d['label']} — {node}", fontsize=9)
            if i == 1:
                ax.set_xlabel("Measured time (s)")
            if j == 0:
                ax.set_ylabel("Predicted time (s)")
    fig.suptitle("Latency prediction on held-out script families (line: perfect; band: within 2×)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK, y=1.01)
    fig.tight_layout()
    save(fig, "fig5_predicted_vs_measured")

    # Fig 6: RTT sensitivity (total time vs network round trip).
    fig, axes = plt.subplots(1, len(ds), figsize=(11, 3.3))
    for ax, d in zip(axes, ds):
        sw = d["rtt_sweep"]
        x = [r["rtt_ms"] for r in sw]
        for p, k in (("edge_only", "edge_only_s"), ("cloud_only", "cloud_only_s"), ("scheduler", "scheduler_s"),
                     ("oracle", "oracle_s")):
            ax.plot(x, [r[k] for r in sw], ls=styles[p], color=COL[p], lw=2.4 if p == "scheduler" else 1.6,
                    label=LABEL[p], marker="o" if p == "scheduler" else None, ms=4)
        ax.axvline(d["rtt_ms"], color=AXIS, lw=1)
        ax.set_xlabel("Network round trip (ms)")
        ax.set_title(d["label"])
        ax.set_ylim(bottom=0)
    axes[0].set_ylabel("Total wall-clock time (s)")
    axes[-1].legend(loc="upper left")
    fig.suptitle("Sensitivity to network latency (vertical line: RTT used elsewhere in this report)", x=0.01,
                 ha="left", fontsize=11, fontweight="bold", color=INK, y=1.03)
    fig.tight_layout()
    save(fig, "fig6_rtt_sensitivity")

    # Fig 7: per-family time saved vs edge-only (asym_v2).
    d = ds[-1]
    moved = [r for r in d["per_family"] if abs(r["oracle_s"] / r["edge_only_s"] - 1) >= 0.005
             or abs(r["scheduler_s"] / r["edge_only_s"] - 1) >= 0.005]
    still = [r["family"] for r in d["per_family"] if r not in moved]
    pf = sorted(moved, key=lambda r: r["scheduler_s"] / r["edge_only_s"], reverse=True)
    fig, ax = plt.subplots(figsize=(7.5, 0.24 * len(pf) + 1.2))
    rel = [100 * (r["scheduler_s"] / r["edge_only_s"] - 1) for r in pf]
    orc = [100 * (r["oracle_s"] / r["edge_only_s"] - 1) for r in pf]
    y = np.arange(len(pf))
    ax.barh(y, rel, height=0.62, color=[COL["scheduler"] if v <= 0 else COL["edge_only"] for v in rel],
            edgecolor=SURF, linewidth=2)
    ax.plot(orc, y, "|", color=INK, ms=12, mew=2, label="Oracle (best possible)")
    ax.set_yticks(y, [f"{r['family']} (n={r['n']})" for r in pf], fontsize=7.5)
    ax.axvline(0, color=AXIS, lw=1)
    ax.grid(axis="y", visible=False)
    for yi, v, ov in zip(y, rel, orc):
        x = min(v, ov)
        ax.text(x - 1.5 if x < 0 else max(v, ov) + 1.5, yi, f"{v:+.0f}%", va="center",
                ha="right" if x < 0 else "left", fontsize=7.5, color=INK2)
    ax.set_xlabel("AI Scheduler total time vs Edge-only, per script family (%)" +
                  (f"\n{len(still)} families where no routing could save time are omitted" if still else ""))
    ax.set_xlim(min(rel + orc) - 14, max(max(rel + orc), 0) + 8)
    ax.legend(loc="lower left")
    ax.set_title(f"Where the time is saved — {d['label']}")
    save(fig, "fig7_per_family")

    # Fig 8: bootstrap distribution of the improvement vs edge-only.
    fig, ax = plt.subplots(figsize=(7.5, 3))
    for d, col in zip(ds, [COL["oracle"], COL["scheduler"], "#6250d6"]):
        s = d["_arrays"]["boot_edge"]
        ax.hist(s, bins=60, color=col, alpha=0.75, label=d["label"], edgecolor=SURF, linewidth=0.5)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_xlabel("AI Scheduler vs Edge-only, total time (%) over bootstrap resamples")
    ax.set_ylabel("Resamples")
    ax.legend()
    ax.set_title("Bootstrap distribution of the improvement over always running on the edge")
    save(fig, "fig8_bootstrap_distribution")
    return sorted(f for f in os.listdir(fdir) if f.endswith(".png"))


# --------------------------------------------------------------------------- report

def write_report(R, md, figs):
    ds = {d["key"]: d for d in R["datasets"]}
    a2, a1, sh = ds["asym_v2"], ds["asym_v1"], ds["similar_hw"]
    o = R["overhead"]
    h = R.get("holdout")

    def s(d, p, k="vs_edge_only_pct"):
        return d["policies"][p][k]

    L = ["# Benchmark evaluation: AI Scheduler vs cloud-only, edge-only and other baselines", "",
         f"Generated by `bench/paper_eval.py` on {R['meta']['generated_at']} (python {R['meta']['python']}, "
         f"scikit-learn {R['meta']['sklearn']}, {R['meta']['bootstrap']} bootstrap resamples). "
         "All policies are scored on **measured** edge and cloud run times. The AI Scheduler and the static-threshold "
         "baseline only use predictions made with the script's whole family held out of training "
         "(grouped K-fold), so these are out-of-sample numbers.", "",
         "## Headline", "",
         f"* **With a real hardware gap** (edge 0.5 CPU vs cloud 4 CPU, 110 ms RTT): the AI Scheduler finishes all "
         f"633 jobs in **{a2['policies']['scheduler']['total_s']:.0f} s**, "
         f"{-s(a2,'scheduler'):.1f}% faster than edge-only "
         f"(95% CI {fmt_ci(a2['bootstrap']['edge_only']['script'])}%) and "
         f"{-s(a2,'scheduler','vs_cloud_only_pct'):.1f}% faster than cloud-only; it is "
         f"{s(a2,'scheduler','regret_vs_oracle_pct'):.1f}% from the oracle "
         f"({s(a2,'scheduler','oracle_efficiency_pct'):.1f}% oracle efficiency).",
         f"* Without the heavy workloads (591 jobs): {s(a1,'scheduler'):+.1f}% vs edge-only "
         f"(CI {fmt_ci(a1['bootstrap']['edge_only']['script'])}%), "
         f"{s(a1,'scheduler','vs_cloud_only_pct'):+.1f}% vs cloud-only.",
         f"* **Routing accuracy** (chose the node that was really faster): "
         f"{100*a2['classification']['scheduler']['accuracy']:.1f}% / "
         f"{100*a1['classification']['scheduler']['accuracy']:.1f}% / "
         f"{100*sh['classification']['scheduler']['accuracy']:.1f}% on the three datasets; "
         f"MCC {_num(a2['classification']['scheduler']['mcc'])} / {_num(a1['classification']['scheduler']['mcc'])} / "
         f"{_num(sh['classification']['scheduler']['mcc'])}. On jobs where the choice matters by ≥10% the accuracy is "
         f"{100*a2['classification']['scheduler_decisive_only']['accuracy']:.1f}% / "
         f"{100*a1['classification']['scheduler_decisive_only']['accuracy']:.1f}% / "
         f"{100*sh['classification']['scheduler_decisive_only']['accuracy']:.1f}%.",
         f"* **Latency-prediction accuracy** (log10 R², families held out): edge "
         f"{a2['regression']['edge']['r2_log10']:.3f}, cloud {a2['regression']['cloud']['r2_log10']:.3f} "
         f"(asymmetric + heavy); median absolute error {100*a2['regression']['edge']['median_ape']:.0f}% edge, "
         f"{100*a2['regression']['cloud']['median_ape']:.0f}% cloud.",
         f"* **Similar hardware** (the original edge vs EC2 data): the cloud is faster on only "
         f"{sh['cloud_wins']}/{sh['scripts']} jobs once RTT is paid, so there is nothing to gain; the scheduler is "
         f"{s(sh,'scheduler'):+.1f}% vs edge-only and {s(sh,'scheduler','vs_cloud_only_pct'):+.1f}% vs cloud-only.",
         f"* **A tuned one-feature heuristic is a strong baseline.** Offloading whenever the static cost estimate "
         f"exceeds a threshold (tuned on training folds) is {s(a1,'heuristic'):+.1f}% vs edge-only on the 591-job "
         f"set, *better* than the AI Scheduler there ({s(a1,'scheduler'):+.1f}%), because the scheduler under-offloads "
         f"(recall {100*a1['classification']['scheduler']['recall_cloud']:.0f}%). On the 633-job set the scheduler "
         f"wins ({s(a2,'scheduler'):+.1f}% vs {s(a2,'heuristic'):+.1f}%), with far fewer wrong offloads "
         f"(precision {100*a2['classification']['scheduler']['precision_cloud']:.0f}% vs "
         f"{100*a2['classification']['heuristic']['precision_cloud']:.0f}%).",
         f"* **Overhead**: one scheduling decision takes {o['p50_ms']:.1f} ms (p50), {o['p95_ms']:.1f} ms (p95).", "",
         "## Table 1 — Policy comparison (total and per-job completion time)", "",
         "Random is the expectation over 1000 coin-flip assignments. *Regret vs oracle* is how much slower than "
         "an all-knowing router. *Decision acc.* is the share of jobs sent to the node that was really faster.", "",
         *md["policies"], "", "![Total time per policy](figures/fig1_policy_total_time.png)", "",
         "![Per-job completion time](figures/fig3_latency_cdf.png)", "",
         "## Table 2 — Routing accuracy (is the cloud faster for this job?)", "",
         "Positive class = *cloud is faster including RTT*. The class balance differs a lot between datasets, so "
         "compare accuracy with the majority-class baseline and read balanced accuracy and MCC. *Decisive* keeps only "
         "jobs where the two nodes differ by at least 10%; on the rest either choice costs under 10%.", "",
         *md["classification"], "", "![Confusion matrices](figures/fig4_confusion_matrices.png)", "",
         "## Table 3 — Latency-prediction accuracy (regression)", "",
         "APE = absolute percentage error. *Within 2×* = prediction within a factor of two of the measured time.", "",
         *md["regression"], "", "![Predicted vs measured](figures/fig5_predicted_vs_measured.png)", "",
         "## Table 4 — Statistical significance", "",
         "Δ total is the change in total time from using the AI Scheduler instead of the baseline (negative = faster), "
         "with 95% bootstrap intervals resampling scripts and, more conservatively, whole families. The Wilcoxon "
         "signed-rank test is on paired per-job times (jobs where both policies made the same choice are tied and "
         "dropped). Rank-biserial r < 0 means the scheduler is faster.", "",
         *md["significance"], "", "![Improvement with CI](figures/fig2_improvement_ci.png)", "",
         "![Bootstrap distribution](figures/fig8_bootstrap_distribution.png)", "",
         "## Table 5 — Datasets and robustness to the validation split", "",
         "Leave-one-family-out trains on every family but one and tests on the one left out, for every family.", "",
         *md["datasets"], "",
         "## Network-latency sensitivity", "",
         "Predictions do not depend on RTT; only the routing rule does, so the sweep re-applies the rule to the same "
         "out-of-fold predictions. Cloud-only degrades linearly with RTT while the scheduler shifts work back "
         "to the edge. From 50 ms upward the scheduler beats both fixed policies on the asymmetric data; near 0 ms "
         "cloud-only is as good or slightly better, and on similar hardware edge-only is always best.", "",
         "| Dataset | RTT (ms) | Edge-only (s) | Cloud-only (s) | AI Scheduler (s) | Oracle (s) | Accuracy | Sent to cloud |",
         "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for d in R["datasets"]:
        for r in d["rtt_sweep"]:
            if r["rtt_ms"] in (0, 10, 50, 110, 200, 500):
                L.append(f"| {d['label']} | {r['rtt_ms']} | {r['edge_only_s']:.1f} | {r['cloud_only_s']:.1f} | "
                         f"{r['scheduler_s']:.1f} | {r['oracle_s']:.1f} | {100*r['accuracy']:.1f}% | "
                         f"{r['cloud_share_pct']:.1f}% |")
    L += ["", "![RTT sensitivity](figures/fig6_rtt_sensitivity.png)", "",
          "## Where the gain comes from", "", "![Per family](figures/fig7_per_family.png)", "",
          "| Dataset | Misrouted jobs | Time lost to misrouting | As share of edge-only total |",
          "| --- | ---: | ---: | ---: |"]
    for d in R["datasets"]:
        m = d["misroute_cost"]
        L.append(f"| {d['label']} | {m['n']} / {d['scripts']} | {m['total_s']:.2f} s (median {m['median_s']:.3f} s) | "
                 f"{m['share_of_edge_total_pct']:.2f}% |")
    if h:
        L += ["", "## Unseen hand-written workloads", "",
              f"On {h['n']} hand-written scripts that the dataset generator never produced (`holdout/`), the static "
              f"cost estimate has Spearman ρ = {h['spearman']:.2f} with measured run time (`bench/holdout.py`). "
              "This is the weakest link: the regressors are only as good as the static features on code unlike the "
              "training families."]
    L += ["", "## How to read these results (threats to validity)", "",
          "* The asymmetric datasets come from two Docker workers on one laptop with different CPU quotas and a "
          "**simulated** 110 ms RTT. They test the decision logic on a real compute gap; they are not an EC2 "
          "measurement. Only the similar-hardware dataset used a real cloud instance.",
          "* The 42 heavy workloads in `asym_v2` were written to exercise the cloud; asym_v1 is the less favourable, "
          "more representative mix. Report both.",
          "* Accuracy alone is misleading on the similar-hardware data (one positive in 495): always answering *edge* "
          "already scores 99.8%. Use balanced accuracy, MCC and the time-based metrics there.",
          "* Each job was timed 3× (median kept); run-to-run noise on sub-50 ms jobs is comparable to the edge/cloud "
          "gap, which is why the *decisive* subset is reported.",
          "* Single collection run per dataset; the bootstrap intervals capture workload variation, not "
          "machine-to-machine variation.", "",
          "## Files", "",
          "* `tables/` — every table as Markdown, CSV, and (tables 1–3) LaTeX `tabular` for the paper.",
          "* `figures/` — every figure as 300-dpi PNG and vector PDF.",
          "* `results.json` — all numbers above, machine-readable.", "",
          f"Figures: {', '.join(figs)}."]
    with open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    import sklearn
    rng = np.random.default_rng(0)
    R = {"meta": {"generated_at": time.strftime("%Y-%m-%d %H:%M"), "python": sys.version.split()[0],
                  "sklearn": sklearn.__version__, "bootstrap": a.bootstrap, "tie_band": TIE_BAND},
         "datasets": []}
    for spec in DATASETS:
        print(f"evaluating {spec[0]} ...", flush=True)
        R["datasets"].append(evaluate(*spec, B=a.bootstrap, rng=rng))
    R["overhead"] = decision_overhead()
    hp = os.path.join(ROOT, "bench", "holdout_results.json")
    if os.path.exists(hp):
        h = json.load(open(hp, encoding="utf-8"))
        R["holdout"] = {"n": h["n"], "spearman": h["spearman"]}
    os.makedirs(OUT, exist_ok=True)
    md = write_tables(R, os.path.join(OUT, "tables"))
    figs = [] if a.no_figures else write_figures(R, os.path.join(OUT, "figures"))
    write_report(R, md, figs)
    for d in R["datasets"]:
        d.pop("_arrays")
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, indent=2)
    print("\n".join(md["policies"] + [""] + md["classification"] + [""] + md["regression"]))
    print(f"\nwrote {OUT}/REPORT.md, results.json, tables/, figures/")


if __name__ == "__main__":
    main()
