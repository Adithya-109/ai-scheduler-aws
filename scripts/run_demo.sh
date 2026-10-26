#!/usr/bin/env bash
# One command for the demo: landing page (8080) -> dashboard (8501), plus a local edge worker (8000).
#   ./scripts/run_demo.sh
# Needs .env with WORKER_API_KEY (and CLOUD_WORKER_URL for the cloud side). Ctrl+C stops everything.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .venv ] && source .venv/bin/activate
set -a; [ -f .env ] && source .env; set +a
export SCHEDULER_MODELS_DIR="${SCHEDULER_MODELS_DIR:-models/asym_v2}"
PIDS=()
trap 'kill "${PIDS[@]}" 2>/dev/null || true' EXIT INT TERM

if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 8000 is already in use: not starting a local worker (stop the other process if the app can't reach the edge)."
else
  python3 worker/worker_server.py & PIDS+=($!)
fi
(cd landing-page && python3 -m http.server 8080 --bind 127.0.0.1 >/dev/null 2>&1) & PIDS+=($!)
sleep 2
(command -v open >/dev/null && open "http://localhost:8080") || echo "Open http://localhost:8080"
streamlit run app.py --server.port 8501 --server.headless true
