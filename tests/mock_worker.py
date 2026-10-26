"""A stdlib HTTP server with the same wire contract as worker_server.py.

FastAPI is optional for the test suite; this exercises the real job runner,
auth check, concurrency slots and the client code over real sockets.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from worker.runner import JobSlots, Limits, health_snapshot, run_job, verify_api_key


class MockWorker:
    def __init__(self, api_key: str = "", max_jobs: int = 2, limits: Limits | None = None, extra_delay_s: float = 0.0,
                 port: int = 0, host: str = "127.0.0.1"):
        self.api_key, self.limits = api_key, limits or Limits(timeout_s=10)
        self.slots = JobSlots(max_jobs)
        self.extra_delay_s = extra_delay_s
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def _send(self, code: int, body: dict, headers: dict | None = None):
                raw = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                if self.path == "/health":
                    self._send(200, health_snapshot(outer.slots))
                else:
                    self._send(404, {"detail": "not found"})

            def do_POST(self):
                if self.path != "/execute":
                    return self._send(404, {"detail": "not found"})
                if not verify_api_key(self.headers.get("X-API-Key"), outer.api_key):
                    return self._send(401, {"detail": "invalid or missing X-API-Key"})
                n = int(self.headers.get("Content-Length", 0))
                code = json.loads(self.rfile.read(n))["code"]
                if not outer.slots.acquire(wait_s=0.5):
                    return self._send(503, {"detail": "worker busy"}, {"Retry-After": "1"})
                try:
                    if outer.extra_delay_s:
                        import time
                        time.sleep(outer.extra_delay_s)
                    self._send(200, run_job(code, outer.limits))
                finally:
                    outer.slots.release()

        self.httpd = ThreadingHTTPServer((host, port), Handler)
        self.url = f"http://{host}:{self.httpd.server_address[1]}"
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
