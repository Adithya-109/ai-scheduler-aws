"""Benchmarks for ai-scheduler-aws.

    python3 bench/run_benchmarks.py            # full run (~1 min), writes bench/results.json + RESULTS.md
    python3 bench/run_benchmarks.py --quick    # CI-sized run

Everything is computed from the repository's own data and models. The cloud
node is never contacted: cloud numbers come from hardware_benchmark.csv and the
RTT stored with the models. B9 re-runs the *pre-overhaul* pipeline (from git
history) on the same scripts so before/after is apples to apples.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import numpy as np  # noqa: E402
import requests  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

from pipeline.dataset import load_benchmark, policy_totals  # noqa: E402
from pipeline.feature_extractor import FEATURE_COLUMNS, CodeFeatureExtractor  # noqa: E402
from pipeline.scheduler import OffloadingScheduler  # noqa: E402
from train_model import EPS, make_regressor  # noqa: E402

V1_COMMIT = "387e55e"
OUT_JSON = os.path.join(ROOT, "bench", "results.json")
OUT_MD = os.path.join(ROOT, "bench", "RESULTS.md")


def pct(xs, p):
    return float(np.percentile(xs, p))


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def b_extraction(codes, repeats):
    ex, lat = CodeFeatureExtractor(), []
    for _ in range(repeats):
        for c in codes:
            t = time.perf_counter()
            ex.analyze(c)
            lat.append((time.perf_counter() - t) * 1e3)
    return {"n": len(lat), "p50_ms": pct(lat, 50), "p95_ms": pct(lat, 95), "max_ms": max(lat)}


def b_schedule(codes):
    t = time.perf_counter()
    s = OffloadingScheduler()
    cold = (time.perf_counter() - t) * 1e3
    for c in codes[:50]:
        s.schedule(c)
    lat = []
    for c in codes:
        t = time.perf_counter()
        s.schedule(c)
        lat.append((time.perf_counter() - t) * 1e3)
    return {"cold_load_ms": cold, "p50_ms": pct(lat, 50), "p95_ms": pct(lat, 95),
            "throughput_per_s": 1000 / statistics.mean(lat)}


def oof_eval(df, rtt):
    X = df[FEATURE_COLUMNS].to_numpy(float)
    e, c = df.actual_edge_time.to_numpy(), df.actual_cloud_time.to_numpy()
    ye, yc = np.log10(e + EPS), np.log10(c + EPS)
    oe, oc = np.zeros(len(df)), np.zeros(len(df))
    for tr, te in GroupKFold(5).split(X, groups=df.family):
        oe[te] = make_regressor().fit(X[tr], ye[tr]).predict(X[te])
        oc[te] = make_regressor().fit(X[tr], yc[tr]).predict(X[te])
    pe, pc = 10 ** oe - EPS, 10 ** oc - EPS
    choose = pc + rtt < pe
    return pe, pc, choose


def b_models(df, rtt):
    e, c = df.actual_edge_time.to_numpy(), df.actual_cloud_time.to_numpy()
    pe, pc, choose = oof_eval(df, rtt)
    real = c + rtt < e
    totals = policy_totals(e, c, rtt, choose)
    ye, yc = np.log10(e + EPS), np.log10(c + EPS)
    from sklearn.metrics import r2_score
    return {
        "rows": len(df), "families": int(df.family.nunique()), "rtt_ms": rtt * 1000,
        "measured_cloud_wins": int(real.sum()),
        "cloud_faster_ignoring_rtt": int((c < e).sum()),
        "median_cloud_over_edge": float(np.median(c / e)),
        "edge_r2_log_grouped": float(r2_score(ye, np.log10(pe + EPS))),
        "cloud_r2_log_grouped": float(r2_score(yc, np.log10(pc + EPS))),
        "edge_median_abs_pct_err": float(np.median(np.abs(pe - e) / e)),
        "cloud_median_abs_pct_err": float(np.median(np.abs(pc - c) / c)),
        "routed_to_cloud": int(choose.sum()),
        "decision_agrees_with_measurement_pct": float(100 * (choose == real).mean()),
        "policy_total_seconds": totals,
        "scheduler_vs_always_edge_pct": 100 * (totals["scheduler"] / totals["always_edge"] - 1),
        "scheduler_vs_always_cloud_pct": 100 * (totals["scheduler"] / totals["always_cloud"] - 1),
        "scheduler_regret_vs_oracle_pct": 100 * (totals["scheduler"] / totals["oracle"] - 1),
    }


def b_rtt_sweep(codes):
    out = {}
    base = {ms: [OffloadingScheduler(cloud_rtt_ms=ms).schedule(c) for c in codes] for ms in (1, 10, 50, 110, 200, 500)}
    for ms, res in base.items():
        res = [r for r in res if "error" not in r]
        out[str(ms)] = {
            "cloud_pct": 100 * float(np.mean([r["decision"] == "CLOUD" for r in res])),
            "decision_matches_predicted_totals": all(
                (r["decision"] == "CLOUD") == (r["predictions"]["predicted_cloud_time"] < r["predictions"]["predicted_edge_time"])
                for r in res),
            "min_confidence": min(r["confidence"] for r in res),
        }
    keys = sorted(base, key=int)
    flips = 0
    for a, b in zip(keys, keys[1:]):
        flips += sum(1 for x, y in zip(base[a], base[b]) if x["decision"] == "EDGE" and y["decision"] == "CLOUD")
    out["edge_to_cloud_flips_when_rtt_rises"] = flips
    return out


def b_worker(n_spawn=30, n_req=40):
    from tests.mock_worker import MockWorker
    from worker.runner import Limits
    lat = []
    for _ in range(n_spawn):
        t = time.perf_counter()
        subprocess.run([sys.executable, "-I", "-c", "pass"], capture_output=True)
        lat.append((time.perf_counter() - t) * 1e3)
    res = {"interpreter_spawn_p50_ms": pct(lat, 50)}
    for jobs in (1, 2, 4):
        with MockWorker(max_jobs=jobs, limits=Limits(timeout_s=10)) as w:
            times, codes_seen = [], []
            lock = threading.Lock()

            def hit():
                t = time.perf_counter()
                r = requests.post(w.url + "/execute", json={"code": "s=0\nfor i in range(200000): s+=i"}, timeout=30)
                with lock:
                    times.append((time.perf_counter() - t) * 1e3)
                    codes_seen.append(r.status_code)

            t0 = time.perf_counter()
            th = [threading.Thread(target=hit) for _ in range(n_req)]
            for t in th:
                t.start()
            for t in th:
                t.join()
            wall = time.perf_counter() - t0
            res[f"concurrent_{jobs}_slots"] = {
                "requests": n_req, "ok": codes_seen.count(200), "busy_503": codes_seen.count(503),
                "wall_s": wall, "p50_ms": pct(times, 50), "p95_ms": pct(times, 95),
                "completed_per_s": codes_seen.count(200) / wall}
    return res


def legacy_pipeline(files):
    """Load the pre-overhaul extractor, predictor and pickles from git history."""
    tmp = tempfile.mkdtemp(prefix="legacy_")
    os.makedirs(os.path.join(tmp, "pipeline"))
    os.makedirs(os.path.join(tmp, "models"))
    for rel in ("pipeline/feature_extractor.py", "pipeline/predictor.py", "models/training_metadata.json",
                "models/scaler.pkl", "models/edge_rf_model.pkl", "models/cloud_rf_model.pkl",
                "models/routing_classifier.pkl"):
        blob = subprocess.check_output(["git", "show", f"{V1_COMMIT}:{rel}"], cwd=ROOT)
        with open(os.path.join(tmp, rel), "wb") as fh:
            fh.write(blob)

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    fe = load("legacy_fe", os.path.join(tmp, "pipeline", "feature_extractor.py"))
    pr = load("legacy_pred", os.path.join(tmp, "pipeline", "predictor.py"))
    ex, pred = fe.CodeFeatureExtractor(), pr.LatencyPredictor()
    out = []
    for f in files:
        feats = ex.analyze(read(os.path.join(ROOT, "test_scripts", f)))
        out.append(pred.predict(feats)["routing_decision"] == "CLOUD")
    return np.array(out)


def b_before_after(df, rtt, new_choose):
    legacy = legacy_pipeline(df.file.tolist())
    e, c = df.actual_edge_time.to_numpy(), df.actual_cloud_time.to_numpy()
    old = policy_totals(e, c, rtt, legacy)
    new = policy_totals(e, c, rtt, new_choose)
    return {
        "rows": len(df),
        "before": {"routed_to_cloud": int(legacy.sum()), "scheduler_s": old["scheduler"],
                   "vs_always_edge_pct": 100 * (old["scheduler"] / old["always_edge"] - 1)},
        "after_out_of_fold": {"routed_to_cloud": int(new_choose.sum()), "scheduler_s": new["scheduler"],
                              "vs_always_edge_pct": 100 * (new["scheduler"] / new["always_edge"] - 1)},
        "always_edge_s": old["always_edge"], "always_cloud_s": old["always_cloud"], "oracle_s": old["oracle"],
        "note": "before = shipped v1 models (trained on these rows) with v1 extractor; "
                "after = v2 features, out-of-fold with whole families held out",
    }


def write_markdown(R):
    m, s, x = R["models"], R["schedule"], R["extraction"]
    t = m["policy_total_seconds"]
    lines = [
        "# Benchmark results", "",
        f"Generated by `bench/run_benchmarks.py` ({R['meta']['mode']} mode, python {R['meta']['python']}, "
        f"scikit-learn {R['meta']['sklearn']}, {R['meta']['cpus']} CPUs). The cloud node was not contacted: cloud times "
        f"come from `hardware_benchmark.csv`.", "",
        "## What the data says", "",
        f"* {m['rows']} scripts with measured edge and cloud times, RTT {m['rtt_ms']:.0f} ms.",
        f"* The cloud beat the edge (compute + RTT < edge) on **{m['measured_cloud_wins']} / {m['rows']}** scripts; "
        f"ignoring RTT it was faster on {m['cloud_faster_ignoring_rtt']}.",
        "* Edge and cloud are similar machines here, so there is little to schedule. Real gains need a real "
        "asymmetry between nodes (docs/DEPLOY.md).", "",
        "## Total wall-clock time, real measurements (held-out script families)", "",
        "| Policy | Total (s) | vs always-edge |", "| --- | ---: | ---: |",
        f"| Oracle (best of each) | {t['oracle']:.1f} | {100*(t['oracle']/t['always_edge']-1):+.1f}% |",
        f"| Always edge | {t['always_edge']:.1f} | baseline |",
        f"| **Scheduler (v2)** | {t['scheduler']:.1f} | {m['scheduler_vs_always_edge_pct']:+.1f}% |",
        f"| Always cloud | {t['always_cloud']:.1f} | {100*(t['always_cloud']/t['always_edge']-1):+.1f}% |", "",
    ]
    if "before_after" in R:
        b = R["before_after"]
        lines += [
            "## Before vs after, same scripts", "",
            "| Pipeline | Routed to cloud | Total (s) | vs always-edge |", "| --- | ---: | ---: | ---: |",
            f"| v1 (classifier + synthetic labels) | {b['before']['routed_to_cloud']} | {b['before']['scheduler_s']:.1f} | "
            f"{b['before']['vs_always_edge_pct']:+.1f}% |",
            f"| v2 (measured-only regressors, out-of-fold) | {b['after_out_of_fold']['routed_to_cloud']} | "
            f"{b['after_out_of_fold']['scheduler_s']:.1f} | {b['after_out_of_fold']['vs_always_edge_pct']:+.1f}% |", "",
            f"_{b['note']}._", ""]
    lines += [
        "## Model quality (out-of-fold, whole families held out)", "",
        "| Metric | Value |", "| --- | ---: |",
        f"| Edge latency R² (log10) | {m['edge_r2_log_grouped']:.3f} |",
        f"| Cloud latency R² (log10) | {m['cloud_r2_log_grouped']:.3f} |",
        f"| Edge median abs % error | {100*m['edge_median_abs_pct_err']:.1f}% |",
        f"| Cloud median abs % error | {100*m['cloud_median_abs_pct_err']:.1f}% |",
        f"| Routing agrees with measured winner | {m['decision_agrees_with_measurement_pct']:.1f}% |", "",
        "## Speed", "",
        "| Step | p50 | p95 |", "| --- | ---: | ---: |",
        f"| AST feature extraction | {x['p50_ms']:.2f} ms | {x['p95_ms']:.2f} ms |",
        f"| Full `schedule()` call | {s['p50_ms']:.2f} ms | {s['p95_ms']:.2f} ms |",
        f"| Model cold load | {s['cold_load_ms']:.0f} ms | |",
        f"| Interpreter spawn per job | {R['worker']['interpreter_spawn_p50_ms']:.1f} ms | |", "",
        "## RTT sensitivity", "",
        "| RTT | Routed to cloud | Decision == predicted totals |", "| ---: | ---: | :---: |"]
    for ms in ("1", "10", "50", "110", "200", "500"):
        r = R["rtt_sweep"][ms]
        lines.append(f"| {ms} ms | {r['cloud_pct']:.1f}% | {'yes' if r['decision_matches_predicted_totals'] else 'NO'} |")
    lines += ["", f"EDGE→CLOUD flips when RTT rises: {R['rtt_sweep']['edge_to_cloud_flips_when_rtt_rises']}", "",
              "## Worker concurrency (local mock over real sockets)", "",
              "| Slots | OK | 503 busy | Wall (s) | p50 (ms) | p95 (ms) | Jobs/s |", "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for jobs in (1, 2, 4):
        w = R["worker"][f"concurrent_{jobs}_slots"]
        lines.append(f"| {jobs} | {w['ok']} | {w['busy_503']} | {w['wall_s']:.2f} | {w['p50_ms']:.0f} | {w['p95_ms']:.0f} | {w['completed_per_s']:.1f} |")
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    import sklearn
    meta = {"mode": "quick" if args.quick else "full", "python": sys.version.split()[0],
            "sklearn": sklearn.__version__, "cpus": os.cpu_count()}
    files = sorted(f for f in os.listdir("test_scripts") if f.endswith(".py"))
    if args.quick:
        files = files[::4]
    codes = [read(os.path.join("test_scripts", f)) for f in files]
    rtt = json.load(open(os.path.join(ROOT, "models", "training_metadata.json")))["measured_rtt_seconds"]
    df = load_benchmark()

    R = {"meta": meta}
    R["extraction"] = b_extraction(codes, 2 if args.quick else 5)
    R["schedule"] = b_schedule(codes)
    R["models"] = b_models(df, rtt)
    R["rtt_sweep"] = b_rtt_sweep(codes if not args.quick else codes[:60])
    R["worker"] = b_worker(n_spawn=10 if args.quick else 30, n_req=16 if args.quick else 40)
    if not args.quick:
        _, _, choose = oof_eval(df, rtt)
        R["before_after"] = b_before_after(df, rtt, choose)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(R, fh, indent=2, default=float)
    write_markdown(R)
    print(open(OUT_MD, encoding="utf-8").read())


if __name__ == "__main__":
    main()
