"""One-off: turn the legacy feature-keyed benchmark CSV into a file-keyed one.

The v1 CSV stored the *old* extractor's features but no script names, so it
could not be re-featurised when the extractor changed. We recover filenames by
re-running the v1 extractor (from git history) over test_scripts/ and keeping
only rows whose v1 feature vector maps to exactly one script and one row.
Rows that cannot be attributed unambiguously are dropped and listed.

    python3 scripts/migrate_dataset.py
"""
import os
import subprocess
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V1_COMMIT = "387e55e"  # last commit with the v1 extractor
LEGACY = os.path.join(ROOT, "data", "legacy_hardware_benchmark_v1.csv")
OUT = os.path.join(ROOT, "hardware_benchmark.csv")
V1_COLS = ["num_lines", "num_loops", "max_loop_depth", "num_operations", "has_heavy_lib",
           "num_function_calls", "num_comprehensions", "max_integer", "estimated_complexity"]


def load_v1_extractor():
    src = subprocess.check_output(
        ["git", "show", f"{V1_COMMIT}:pipeline/feature_extractor.py"], cwd=ROOT, text=True)
    ns: dict = {"__name__": "v1_extractor"}
    exec(compile(src, "v1_extractor", "exec"), ns)  # trusted: our own history
    return ns["CodeFeatureExtractor"]()


def key(row) -> tuple:
    return tuple(round(float(row[c]), 6) for c in V1_COLS)


def main() -> None:
    if not os.path.exists(LEGACY):
        os.makedirs(os.path.dirname(LEGACY), exist_ok=True)
        subprocess.check_call(["git", "mv", "hardware_benchmark.csv", LEGACY], cwd=ROOT)
    legacy = pd.read_csv(LEGACY)
    ex = load_v1_extractor()
    files = sorted(f for f in os.listdir(os.path.join(ROOT, "test_scripts")) if f.endswith(".py"))
    by_key: dict[tuple, list[str]] = {}
    for f in files:
        with open(os.path.join(ROOT, "test_scripts", f), encoding="utf-8") as fh:
            feats = ex.analyze(fh.read())
        by_key.setdefault(key(feats), []).append(f)
    rows_by_key: dict[tuple, list[int]] = {}
    for i, r in legacy.iterrows():
        rows_by_key.setdefault(key(r), []).append(i)

    out, dropped = [], []
    for k, idx in rows_by_key.items():
        cand = by_key.get(k, [])
        if len(idx) == 1 and len(cand) == 1:
            r = legacy.loc[idx[0]]
            out.append({"file": cand[0], "actual_edge_time": r.actual_edge_time,
                        "actual_cloud_time": r.actual_cloud_time, "source": "migrated_v1"})
        else:
            dropped.extend(idx)
    df = pd.DataFrame(out).sort_values("file")
    df.to_csv(OUT, index=False)
    print(f"legacy rows: {len(legacy)}  migrated: {len(df)}  dropped as ambiguous: {len(dropped)}")
    print("Re-run collect_data.py against real hardware to refresh these with repeats + metadata.")


if __name__ == "__main__":
    sys.exit(main())
