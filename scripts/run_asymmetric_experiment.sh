#!/usr/bin/env bash
# Measure every script on a weak "edge" and a stronger "cloud" worker, retrain, benchmark.
#
#   MODE=docker ./scripts/run_asymmetric_experiment.sh     # needs Docker (macOS/Linux)
#   MODE=local  ./scripts/run_asymmetric_experiment.sh     # Linux only: pins processes to CPU cores with taskset
#
# Knobs: EDGE_CPUS (0.5)  CLOUD_CPUS (4)  REPEATS (3)  ONLY ('*')  RTT_MS (110)
#
# Both workers run on THIS machine, so the nodes differ in CPU allowance but the
# network does not: the WAN round trip is a simulated constant (RTT_MS), passed to
# training. This tests the scheduler on a real compute asymmetry; it is not a
# measurement of EC2. For that, point CLOUD_WORKER_URL at a real instance and run
# collect_data.py directly (docs/DEPLOY.md).
#
# Results land on a new branch-free output dir, never over hardware_benchmark.csv:
#   experiments/<timestamp>/{asym_benchmark.csv, *.meta.json, results.txt}
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="${MODE:-docker}"; EDGE_CPUS="${EDGE_CPUS:-0.5}"; CLOUD_CPUS="${CLOUD_CPUS:-4}"
REPEATS="${REPEATS:-3}"; ONLY="${ONLY:-*}"; RTT_MS="${RTT_MS:-110}"
EDGE_PORT=18000; CLOUD_PORT=18001
OUT="experiments/$(date +%Y%m%d-%H%M%S)"; mkdir -p "$OUT"
KEY="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
PIDS=(); CONTS=()
cleanup() {
  for p in "${PIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null || true; done
  for c in "${CONTS[@]:-}"; do [ -n "$c" ] && docker rm -f "$c" >/dev/null 2>&1 || true; done
}
trap cleanup EXIT

wait_up() { for _ in $(seq 1 60); do curl -fsS "http://127.0.0.1:$1/health" >/dev/null 2>&1 && return 0; sleep 1; done; echo "worker on :$1 did not start" >&2; exit 1; }

if [ "$MODE" = docker ]; then
  docker build -q -f worker/Dockerfile -t scheduler-worker .
  run() {  # name port cpus
    docker run -d --name "$1" -p "127.0.0.1:$2:8000" --cpus "$3" --memory 2g \
      -e WORKER_API_KEY="$KEY" -e WORKER_HOST=0.0.0.0 -e WORKER_MAX_JOBS=1 \
      -e OPENBLAS_NUM_THREADS="$4" -e OMP_NUM_THREADS="$4" \
      --read-only --tmpfs /tmp:size=512m --cap-drop ALL --security-opt no-new-privileges:true --pids-limit 512 \
      scheduler-worker >/dev/null
    CONTS+=("$1")
  }
  docker rm -f sched-edge sched-cloud >/dev/null 2>&1 || true
  EDGE_THREADS=$(python3 -c "import math;print(max(1,math.ceil($EDGE_CPUS)))")
  run sched-edge "$EDGE_PORT" "$EDGE_CPUS" "$EDGE_THREADS"
  run sched-cloud "$CLOUD_PORT" "$CLOUD_CPUS" "${CLOUD_CPUS%.*}"
  DESC_E="docker --cpus=$EDGE_CPUS"; DESC_C="docker --cpus=$CLOUD_CPUS"
else
  N=$(nproc); CLOUD_N=$(( N < ${CLOUD_CPUS%.*} ? N : ${CLOUD_CPUS%.*} ))
  CLOUD_SET="0-$((CLOUD_N-1))"
  WORKER_API_KEY="$KEY" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
    taskset -c 0 python3 scripts/stdlib_worker.py --port $EDGE_PORT --jobs 1 & PIDS+=($!)
  WORKER_API_KEY="$KEY" OPENBLAS_NUM_THREADS=$CLOUD_N OMP_NUM_THREADS=$CLOUD_N \
    taskset -c "$CLOUD_SET" python3 scripts/stdlib_worker.py --port $CLOUD_PORT --jobs 1 & PIDS+=($!)
  DESC_E="taskset core 0, 1 thread"; DESC_C="taskset cores $CLOUD_SET"
fi
wait_up $EDGE_PORT; wait_up $CLOUD_PORT

export WORKER_API_KEY="$KEY" CLOUD_WORKER_URL="http://127.0.0.1:$CLOUD_PORT"
export EDGE_DESCRIPTION="$DESC_E" CLOUD_INSTANCE_TYPE="$DESC_C (simulated cloud, local)"
python3 collect_data.py --repeats "$REPEATS" --only "$ONLY" --edge-url "http://127.0.0.1:$EDGE_PORT" \
  --output "$OUT/asym_benchmark.csv" | tee "$OUT/collect.log" | tail -3

python3 bench/asym_report.py "$OUT/asym_benchmark.csv" --rtt-ms "$RTT_MS" | tee "$OUT/results.txt"
echo "Done. Results in $OUT/"
