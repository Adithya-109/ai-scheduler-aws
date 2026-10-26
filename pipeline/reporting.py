"""Numbers shown in the UI, computed from the trained metadata and the
benchmark data rather than typed into the page."""
from __future__ import annotations

import json
import os
import time

import numpy as np

from pipeline.dataset import ROOT, SCRIPTS_DIR, load_benchmark
from pipeline.feature_extractor import CodeFeatureExtractor

META_PATH = os.path.join(os.environ.get("SCHEDULER_MODELS_DIR") or os.path.join(ROOT, "models"),
                         "training_metadata.json")


def load_metadata() -> dict:
    try:
        with open(META_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def measure_extraction_ms(max_scripts: int = 60) -> float:
    """Median time to analyse a script, measured here and now."""
    ex = CodeFeatureExtractor()
    names = sorted(f for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py"))[:max_scripts]
    codes = []
    for n in names:
        with open(os.path.join(SCRIPTS_DIR, n), encoding="utf-8") as fh:
            codes.append(fh.read())
    times = []
    for c in codes:
        t0 = time.perf_counter()
        ex.analyze(c)
        times.append((time.perf_counter() - t0) * 1000)
    return float(np.median(times)) if times else float("nan")


def summary() -> dict:
    meta = load_metadata()
    cv = meta.get("cv", {})
    totals = cv.get("policy_total_seconds", {})
    n = meta.get("training_samples", 0)
    sched_vs_edge = cv.get("scheduler_vs_always_edge_pct")
    return {
        "scripts": n,
        "rtt_ms": meta.get("measured_rtt_ms", 110.0),
        "edge_r2": cv.get("edge_r2_log_grouped"),
        "cloud_r2": cv.get("cloud_r2_log_grouped"),
        "cloud_wins": cv.get("measured_cloud_wins", 0),
        "routed_to_cloud": cv.get("routed_to_cloud", 0),
        "sched_vs_edge_pct": sched_vs_edge,
        "totals": totals,
        "extract_ms": measure_extraction_ms(),
        "model_type": meta.get("model_type", "unknown"),
    }


def fmt_pct(v: float | None, signed: bool = True) -> str:
    return "n/a" if v is None else (f"{v:+.1f}%" if signed else f"{v:.1f}%")


def crossover_curve(rtt_ms: float, bins: int = 8) -> dict:
    """Measured edge time vs measured cloud time + RTT, binned by estimated
    complexity (median per bin). Real timings, not an illustration."""
    df = load_benchmark()
    if df.empty:
        return {"x": [], "edge": [], "cloud_plus_rtt": []}
    df = df.assign(bin=np.digitize(df.estimated_complexity, np.quantile(df.estimated_complexity,
                                                                       np.linspace(0, 1, bins + 1)[1:-1])))
    g = df.groupby("bin")
    return {
        "x": [round(float(v), 2) for v in g.estimated_complexity.median()],
        "edge": [round(float(v), 4) for v in g.actual_edge_time.median()],
        "cloud_plus_rtt": [round(float(v) + rtt_ms / 1000.0, 4) for v in g.actual_cloud_time.median()],
    }


def live_log_summary(records: list[dict], recent: int = 15) -> dict:
    """Aggregate what the running system has actually done (the decision log).

    ``pred_vs_actual_median_abs_pct`` compares the compute time predicted for the
    chosen side with the worker-reported time, over runs that completed cleanly.
    """
    ok = [r for r in records if r.get("compute_time_s") is not None and not r.get("timed_out")
          and r.get("returncode", 0) == 0]
    errs = []
    for r in ok:
        p = r.get("predictions", {})
        pred = p.get("predicted_cloud_compute" if r.get("target") == "cloud" else "predicted_edge_compute")
        if pred and r["compute_time_s"] > 0:
            errs.append(abs(pred - r["compute_time_s"]) / r["compute_time_s"])
    rows = [{
        "time": time.strftime("%H:%M:%S", time.localtime(r.get("ts", 0))),
        "decision": r.get("decision"), "ran_on": r.get("target"),
        "confidence": round(float(r.get("confidence", 0)), 3),
        "predicted_s": (r.get("predictions", {}).get(
            "predicted_cloud_compute" if r.get("target") == "cloud" else "predicted_edge_compute")),
        "actual_s": r.get("compute_time_s"),
        "fallback": r.get("fallback_reason") or "",
        "explored": bool(r.get("explored")),
    } for r in records[-recent:]][::-1]
    return {
        "runs": len(records),
        "on_cloud": sum(r.get("target") == "cloud" for r in records),
        "fallbacks": sum(bool(r.get("fallback")) for r in records),
        "explored": sum(bool(r.get("explored")) for r in records),
        "pred_vs_actual_median_abs_pct": float(np.median(errs) * 100) if errs else None,
        "recent": rows,
    }
