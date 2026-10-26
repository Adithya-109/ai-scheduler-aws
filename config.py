"""Runtime configuration, read from environment variables (and an optional .env).

Nothing secret or environment-specific (IP addresses, API keys) lives in the
source tree. Copy ``.env.example`` to ``.env`` and fill it in.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    """Minimal KEY=VALUE parser so we don't need python-dotenv.

    Existing environment variables win over the file.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


LOCAL_WORKER_URL = _env("LOCAL_WORKER_URL", "http://localhost:8000")
CLOUD_WORKER_URL = _env("CLOUD_WORKER_URL")  # no default: must be configured
WORKER_API_KEY = _env("WORKER_API_KEY")
DECISION_LOG = _env("DECISION_LOG", str(ROOT / "logs" / "decisions.jsonl"))


def execute_url(base_url: str) -> str:
    """Return the /execute endpoint for a worker base URL ('' if unset)."""
    if not base_url:
        return ""
    base = base_url.rstrip("/")
    return base if base.endswith("/execute") else base + "/execute"


def health_url(base_url: str) -> str:
    if not base_url:
        return ""
    base = base_url.rstrip("/")
    if base.endswith("/execute"):
        base = base[: -len("/execute")]
    return base + "/health"


def auth_headers(api_key: str | None = None) -> dict[str, str]:
    key = WORKER_API_KEY if api_key is None else api_key
    return {"X-API-Key": key} if key else {}


def cloud_configured() -> bool:
    return bool(CLOUD_WORKER_URL)
