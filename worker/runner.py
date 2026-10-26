"""Job execution core for the worker. No web framework imports on purpose, so
it can be unit-tested and reused by any front end.

SECURITY NOTE: this executes arbitrary Python. The limits below (rlimits, a
scrubbed environment, a private working directory, a process-group kill on
timeout) reduce the blast radius of a buggy or hostile script but are NOT a
sandbox. Run the worker in a container / dedicated VM with no credentials and
with outbound traffic blocked at the network layer (see docs/DEPLOY.md).
"""
from __future__ import annotations

import hmac
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    timeout_s: float = 30.0
    mem_mb: int = 2048
    max_output_bytes: int = 1_000_000
    max_code_bytes: int = 200_000
    max_file_mb: int = 50

    @classmethod
    def from_env(cls) -> "Limits":
        e = os.environ.get
        return cls(
            timeout_s=float(e("WORKER_TIMEOUT_S", cls.timeout_s)),
            mem_mb=int(e("WORKER_MEM_MB", cls.mem_mb)),
            max_output_bytes=int(e("WORKER_MAX_OUTPUT_BYTES", cls.max_output_bytes)),
            max_code_bytes=int(e("WORKER_MAX_CODE_BYTES", cls.max_code_bytes)),
        )


def verify_api_key(provided: str | None, expected: str) -> bool:
    """Constant-time key check. An empty expected key means auth is off."""
    if not expected:
        return True
    if not provided:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())


class JobSlots:
    """Bounded concurrency + a live count of running jobs (for /health)."""

    def __init__(self, max_jobs: int):
        self.max_jobs = max(1, max_jobs)
        self._sem = threading.BoundedSemaphore(self.max_jobs)
        self._lock = threading.Lock()
        self._active = 0

    @property
    def active(self) -> int:
        with self._lock:
            return self._active

    def acquire(self, wait_s: float = 0.0) -> bool:
        ok = self._sem.acquire(timeout=wait_s) if wait_s > 0 else self._sem.acquire(blocking=False)
        if ok:
            with self._lock:
                self._active += 1
        return ok

    def release(self) -> None:
        with self._lock:
            self._active -= 1
        self._sem.release()


def _child_env(workdir: str) -> dict[str, str]:
    # Deliberately NOT inheriting os.environ: that would leak WORKER_API_KEY
    # and any cloud credentials to the submitted code.
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": workdir,
        "TMPDIR": workdir,
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "1"),
    }


def _preexec(limits: Limits, timeout_s: float):
    def apply() -> None:  # runs in the child between fork and exec
        try:
            import resource

            mem = limits.mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
            cpu = int(timeout_s) + 5
            resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
            fsize = limits.max_file_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        except Exception:  # non-POSIX or restricted: run without rlimits
            pass

    return apply


def _truncate(data: str | bytes | None, cap: int) -> tuple[str, bool]:
    if data is None:
        return "", False
    if isinstance(data, bytes):
        data = data.decode("utf-8", "replace")
    if len(data) > cap:
        return data[:cap] + "\n...[truncated]", True
    return data, False


def run_job(code: str, limits: Limits | None = None, timeout_s: float | None = None) -> dict:
    """Run ``code`` in a fresh interpreter and report what happened.

    The response ALWAYS carries ``execution_time_seconds``, ``returncode`` and
    ``timed_out`` so callers can tell a real measurement from a crash/timeout.
    """
    limits = limits or Limits()
    timeout = limits.timeout_s if timeout_s is None else timeout_s

    if len(code.encode("utf-8", "replace")) > limits.max_code_bytes:
        return {
            "stdout": "", "stderr": "code exceeds WORKER_MAX_CODE_BYTES",
            "execution_time_seconds": 0.0, "returncode": -1,
            "timed_out": False, "truncated": False, "rejected": True,
        }

    with tempfile.TemporaryDirectory(prefix="job_") as workdir:
        start = time.perf_counter()
        timed_out = False
        proc = subprocess.Popen(
            [sys.executable, "-I", "-c", code],
            cwd=workdir,
            env=_child_env(workdir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,  # own process group so we can kill children too
            preexec_fn=_preexec(limits, timeout) if os.name == "posix" else None,
        )
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, AttributeError):
                proc.kill()
            out, err = proc.communicate()
        elapsed = time.perf_counter() - start

    stdout, t1 = _truncate(out, limits.max_output_bytes)
    stderr, t2 = _truncate(err, limits.max_output_bytes)
    if timed_out:
        stderr = (stderr + f"\nTimed out after {timeout:g}s").strip()
    return {
        "stdout": stdout,
        "stderr": stderr,
        "execution_time_seconds": round(elapsed, 4),
        "returncode": -9 if timed_out else proc.returncode,
        "timed_out": timed_out,
        "truncated": t1 or t2,
    }


def health_snapshot(slots: JobSlots) -> dict:
    try:
        load1 = os.getloadavg()[0]
    except (OSError, AttributeError):
        load1 = None
    return {
        "status": "ok",
        "active_jobs": slots.active,
        "max_jobs": slots.max_jobs,
        "cpu_count": os.cpu_count() or 1,
        "load1": load1,
    }
