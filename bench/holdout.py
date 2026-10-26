"""Unseen-workload holdout: hand-written scripts that did not come from the
dataset generator. Measures local runtime, runs the static extractor, and
reports rank correlation between estimated complexity and measured time."""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from pipeline.feature_extractor import CodeFeatureExtractor  # noqa: E402

HOLD = os.path.join(ROOT, "holdout")


def spearman(a, b) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def run_time(path: str, reps: int = 3) -> float:
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        subprocess.run([sys.executable, "-I", path], capture_output=True, check=True, timeout=120)
        ts.append(time.perf_counter() - t0)
    return statistics.median(ts)


def main() -> dict:
    ex = CodeFeatureExtractor()
    rows = []
    for f in sorted(os.listdir(HOLD)):
        if not f.endswith(".py"):
            continue
        p = os.path.join(HOLD, f)
        code = open(p, encoding="utf-8").read()
        feats = ex.analyze(code)
        rows.append({"file": f, "complexity": feats["estimated_complexity"],
                     "seconds": run_time(p), "degraded": bool(feats.get("analysis_degraded"))})
    rho = spearman([r["complexity"] for r in rows], [r["seconds"] for r in rows])
    out = {"n": len(rows), "spearman": rho, "rows": rows}
    with open(os.path.join(ROOT, "bench", "holdout_results.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    return out


if __name__ == "__main__":
    o = main()
    for r in sorted(o["rows"], key=lambda r: r["seconds"]):
        print(f"{r['file']:22s} cx={r['complexity']:6.2f} t={r['seconds']:7.3f}s {'DEGRADED' if r['degraded'] else ''}")
    print(f"\nSpearman(complexity, runtime) = {o['spearman']:.3f} over {o['n']} unseen scripts")
