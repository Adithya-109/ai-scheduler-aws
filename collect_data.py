"""Measure every script in test_scripts/ on the edge and on the cloud worker.

    CLOUD_WORKER_URL=http://<ip>:8000 WORKER_API_KEY=... python3 collect_data.py
    python3 collect_data.py --repeats 5 --only 'numpy_*' --output hardware_benchmark.csv

Each script runs ``--repeats`` times per side; we keep the median and the
spread. Failed or timed-out runs are dropped (and listed) instead of being
recorded as fast successes. A sidecar ``*.meta.json`` records the hardware and
software behind the numbers, so a dataset can always be traced to its machines.

For the scheduler to have anything to learn, the edge and cloud nodes must
actually differ (e.g. a Raspberry Pi / ``docker --cpus=0.5`` edge vs a
compute-optimised EC2 instance). See docs/DEPLOY.md.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import platform
import socket
import statistics
import sys
import time

import pandas as pd
import requests

import config
from worker.runner import Limits, run_job

ROOT = os.path.dirname(os.path.abspath(__file__))


def cpu_model() -> str:
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as fh:
            for line in fh:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def run_edge(code: str, timeout: float) -> dict:
    return run_job(code, Limits(timeout_s=timeout))


def run_cloud(code: str, url: str, timeout: float) -> dict:
    r = requests.post(url, json={"code": code}, headers=config.auth_headers(), timeout=timeout + 30)
    r.raise_for_status()
    return r.json()


def measure(runner, repeats: int):
    """Return (median_seconds, stdev_seconds, error_or_None)."""
    times = []
    for _ in range(repeats):
        res = runner()
        if res.get("timed_out") or res.get("returncode", 0) != 0:
            return None, None, f"returncode={res.get('returncode')} timed_out={res.get('timed_out')}"
        times.append(res["execution_time_seconds"])
    return statistics.median(times), (statistics.stdev(times) if len(times) > 1 else 0.0), None


def probe_rtt(health_url: str, n: int = 9) -> float | None:
    samples = []
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            requests.get(health_url, timeout=10).raise_for_status()
        except requests.RequestException:
            continue
        samples.append(time.perf_counter() - t0)
    return statistics.median(samples) if samples else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--only", default="*", help="glob over script filenames")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--edge-url", default="",
                    help="measure the edge through a worker at this URL (e.g. a CPU-limited container) "
                         "instead of in this process")
    ap.add_argument("--output", default=os.path.join(ROOT, "hardware_benchmark.csv"))
    args = ap.parse_args()

    cloud_url = config.execute_url(config.CLOUD_WORKER_URL)
    if not cloud_url:
        print("CLOUD_WORKER_URL is not set (see .env.example).", file=sys.stderr)
        return 2

    edge_url = config.execute_url(args.edge_url)
    scripts_dir = os.path.join(ROOT, "test_scripts")
    files = sorted(f for f in os.listdir(scripts_dir) if f.endswith(".py") and fnmatch.fnmatch(f, args.only))
    rtt = probe_rtt(config.health_url(config.CLOUD_WORKER_URL))
    print(f"{len(files)} scripts, {args.repeats} repeats per side, RTT={'n/a' if rtt is None else f'{rtt*1000:.1f} ms'}")

    rows, dropped = [], []
    for i, name in enumerate(files, 1):
        with open(os.path.join(scripts_dir, name), encoding="utf-8") as fh:
            code = fh.read()
        e_med, e_sd, e_err = measure(
            (lambda: run_cloud(code, edge_url, args.timeout)) if edge_url else (lambda: run_edge(code, args.timeout)),
            args.repeats)
        try:
            c_med, c_sd, c_err = measure(lambda: run_cloud(code, cloud_url, args.timeout), args.repeats)
        except requests.RequestException as ex:
            c_med = c_sd = None
            c_err = f"{type(ex).__name__}: {ex}"
        if e_err or c_err:
            dropped.append((name, e_err or c_err))
            print(f"[{i}/{len(files)}] {name}: DROPPED ({e_err or c_err})")
            continue
        rows.append({"file": name, "actual_edge_time": e_med, "actual_cloud_time": c_med,
                     "edge_std": e_sd, "cloud_std": c_sd, "repeats": args.repeats, "source": "collect_data"})
        print(f"[{i}/{len(files)}] {name}: edge={e_med:.3f}s cloud={c_med:.3f}s")

    if not rows:
        print("No successful measurements; nothing written.", file=sys.stderr)
        return 1
    pd.DataFrame(rows).to_csv(args.output, index=False)

    try:
        cloud_health = requests.get(config.health_url(config.CLOUD_WORKER_URL), timeout=10).json()
    except (requests.RequestException, ValueError):
        cloud_health = None
    meta = {
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scripts": len(rows), "dropped": dropped, "repeats": args.repeats, "rtt_seconds": rtt,
        "edge": {"host": socket.gethostname(), "cpu": cpu_model(), "cpu_count": os.cpu_count(),
                 "python": platform.python_version(), "description": os.environ.get("EDGE_DESCRIPTION", "")},
        "cloud": {"health": cloud_health, "instance_type": os.environ.get("CLOUD_INSTANCE_TYPE", ""),
                  "url_host": config.CLOUD_WORKER_URL.split("//")[-1].split(":")[0] and "configured"},
    }
    with open(os.path.splitext(args.output)[0] + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(f"wrote {len(rows)} rows to {args.output} ({len(dropped)} dropped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
