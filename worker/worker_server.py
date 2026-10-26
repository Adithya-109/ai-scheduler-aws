"""FastAPI front end for the worker. Keep it thin: logic lives in runner.py.

Run:  WORKER_API_KEY=... WORKER_HOST=0.0.0.0 python worker/worker_server.py
"""
from __future__ import annotations

import os
import sys

# Allow `python worker/worker_server.py` as well as `python -m worker.worker_server`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Header, HTTPException  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from worker.runner import (  # noqa: E402
    JobSlots,
    Limits,
    health_snapshot,
    run_job,
    verify_api_key,
)

API_KEY = os.environ.get("WORKER_API_KEY", "")
LIMITS = Limits.from_env()
SLOTS = JobSlots(int(os.environ.get("WORKER_MAX_JOBS", os.cpu_count() or 1)))

app = FastAPI(title="AI Scheduler worker")


class CodePayload(BaseModel):
    code: str


@app.get("/health")
def health():
    # Unauthenticated and cheap: used for RTT probing and load reporting.
    return health_snapshot(SLOTS)


@app.post("/execute")
def execute(payload: CodePayload, x_api_key: str | None = Header(default=None)):
    if not verify_api_key(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")
    if not SLOTS.acquire(wait_s=2.0):
        raise HTTPException(status_code=503, detail="worker busy", headers={"Retry-After": "1"})
    try:
        return run_job(payload.code, LIMITS)
    finally:
        SLOTS.release()


def _is_loopback(host: str) -> bool:
    return host in ("127.0.0.1", "::1", "localhost")


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("WORKER_HOST", "127.0.0.1")
    port = int(os.environ.get("WORKER_PORT", "8000"))
    if not API_KEY and not _is_loopback(host):
        sys.exit("Refusing to listen on %s without WORKER_API_KEY: this endpoint runs "
                 "arbitrary code. Set WORKER_API_KEY or bind to 127.0.0.1." % host)
    uvicorn.run(app, host=host, port=port)
