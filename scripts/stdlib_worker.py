"""Run a worker with only the standard library (same wire contract as worker_server.py).

For machines where FastAPI is not installed. Usage:
    WORKER_API_KEY=k python3 scripts/stdlib_worker.py --port 18000 --jobs 1
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.mock_worker import MockWorker  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, required=True)
ap.add_argument("--jobs", type=int, default=1)
a = ap.parse_args()
with MockWorker(api_key=os.environ.get("WORKER_API_KEY", ""), max_jobs=a.jobs, port=a.port):
    print(f"stdlib worker on :{a.port}", flush=True)
    while True:
        time.sleep(3600)
