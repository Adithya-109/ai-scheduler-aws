"""Merge benchmark CSVs collected on the SAME pair of workers into one dataset.

    python3 scripts/merge_datasets.py data/docker_asym_v1 experiments/<ts> --out data/docker_asym_v2

Each input is a directory holding asym_benchmark.csv and asym_benchmark.meta.json.
Refuses to merge runs whose hardware description differs (mixing machines would
poison the labels). A script present in more than one input keeps the LAST value.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd


def load(d: str):
    csv = pd.read_csv(os.path.join(d, "asym_benchmark.csv"))
    with open(os.path.join(d, "asym_benchmark.meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    return csv, meta


def hardware(meta: dict) -> tuple:
    return (meta.get("edge", {}).get("description"), meta.get("cloud", {}).get("instance_type"),
            meta.get("edge", {}).get("cpu_count"), meta.get("cloud", {}).get("health", {}).get("cpu_count"))


def merge(dirs: list[str]):
    frames, metas = zip(*(load(d) for d in dirs))
    hw = {hardware(m) for m in metas}
    if len(hw) != 1:
        raise SystemExit(f"refusing to merge runs from different hardware: {sorted(map(str, hw))}")
    df = pd.concat(frames, ignore_index=True).drop_duplicates("file", keep="last").sort_values("file")
    meta = dict(metas[-1])
    meta["scripts"] = len(df)
    meta["merged_from"] = [os.path.basename(os.path.normpath(d)) for d in dirs]
    meta["collected_at_each"] = [m.get("collected_at") for m in metas]
    return df.reset_index(drop=True), meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    df, meta = merge(a.dirs)
    os.makedirs(a.out, exist_ok=True)
    df.to_csv(os.path.join(a.out, "asym_benchmark.csv"), index=False)
    with open(os.path.join(a.out, "asym_benchmark.meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(f"wrote {len(df)} rows to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
