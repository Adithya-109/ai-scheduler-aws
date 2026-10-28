"""Benchmark dataset loading. Features are recomputed from the scripts every
time, so changing the extractor never leaves stale feature columns behind."""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import pandas as pd

from pipeline.feature_extractor import FEATURE_COLUMNS, FEATURE_VERSION, CodeFeatureExtractor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, "hardware_benchmark.csv")
SCRIPTS_DIR = os.path.join(ROOT, "test_scripts")


def family_of(filename: str) -> str:
    """Script family used for grouped cross-validation.

    Hand-written families (loop_*, fib_*, ...) are one group each. The ~450
    generated ``script_NNN`` programs are bucketed by number so they spread
    over several folds instead of forming one giant group.
    """
    stem = filename[:-3] if filename.endswith(".py") else filename
    head = stem.split("_")[0] if not stem.startswith("numpy_") else "_".join(stem.split("_")[:2])
    if head == "script":
        digits = "".join(ch for ch in stem if ch.isdigit()) or "0"
        return f"script{int(digits) % 8}"
    return head


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def load_benchmark(csv_path: str = DATA_FILE, scripts_dir: str = SCRIPTS_DIR) -> pd.DataFrame:
    raw = pd.read_csv(csv_path)
    if "file" not in raw.columns:
        raise ValueError(f"{csv_path} has no 'file' column; run scripts/migrate_dataset.py or collect_data.py")
    ex = CodeFeatureExtractor()
    rows = []
    for _, r in raw.iterrows():
        path = os.path.join(scripts_dir, r["file"])
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            feats = ex.analyze(fh.read())
        if "error" in feats:
            continue
        row = {c: feats[c] for c in FEATURE_COLUMNS}
        row.update(file=r["file"], family=family_of(r["file"]),
                   actual_edge_time=float(r["actual_edge_time"]),
                   actual_cloud_time=float(r["actual_cloud_time"]))
        if "cloud_wall_time" in raw.columns and pd.notna(r["cloud_wall_time"]):
            row["cloud_wall_time"] = float(r["cloud_wall_time"])
        rows.append(row)
    return pd.DataFrame(rows)


def load_decision_log(path: str) -> pd.DataFrame:
    """Rows logged by the dispatcher: bandit feedback (one side observed)."""
    if not path or not os.path.exists(path):
        return pd.DataFrame()
    recs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("feature_version") != FEATURE_VERSION or rec.get("fallback") or rec.get("returncode", 0) != 0:
                continue
            if rec.get("compute_time_s") is None or "features" not in rec:
                continue
            row = {c: rec["features"].get(c, 0) for c in FEATURE_COLUMNS}
            row.update(target=rec.get("target"), compute_time_s=float(rec["compute_time_s"]))
            recs.append(row)
    return pd.DataFrame(recs)


def policy_totals(edge: np.ndarray, cloud: np.ndarray, rtt: float, choose_cloud: np.ndarray) -> dict:
    """Total wall-clock time of every policy, using *measured* times."""
    cloud_total = cloud + rtt
    return {
        "oracle": float(np.minimum(edge, cloud_total).sum()),
        "always_edge": float(edge.sum()),
        "always_cloud": float(cloud_total.sum()),
        "scheduler": float(np.where(choose_cloud, cloud_total, edge).sum()),
    }
