#!/usr/bin/env bash
# Provision the cloud worker on a fresh Ubuntu EC2 instance.
#   WORKER_API_KEY=<secret> REPO_URL=https://github.com/<you>/ai-scheduler-aws.git bash ec2_setup.sh
# Read docs/DEPLOY.md first: the security group and instance settings matter more than this script.
set -euo pipefail
: "${WORKER_API_KEY:?set WORKER_API_KEY (python3 -c 'import secrets;print(secrets.token_urlsafe(32))')}"
: "${REPO_URL:?set REPO_URL}"
BRANCH="${BRANCH:-main}"

sudo apt-get update -y
sudo apt-get install -y docker.io git
sudo systemctl enable --now docker

rm -rf ~/ai-scheduler-aws
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" ~/ai-scheduler-aws
cd ~/ai-scheduler-aws
sudo docker build -f worker/Dockerfile -t scheduler-worker .

sudo docker rm -f scheduler-worker 2>/dev/null || true
sudo docker run -d --name scheduler-worker --restart unless-stopped \
  -p 8000:8000 \
  -e WORKER_API_KEY="$WORKER_API_KEY" -e WORKER_HOST=0.0.0.0 \
  -e WORKER_MAX_JOBS="${WORKER_MAX_JOBS:-$(nproc)}" -e WORKER_MEM_MB="${WORKER_MEM_MB:-2048}" \
  -e OMP_NUM_THREADS="${OMP_NUM_THREADS:-$(nproc)}" \
  --read-only --tmpfs /tmp:size=512m \
  --cap-drop ALL --security-opt no-new-privileges:true --pids-limit 512 \
  scheduler-worker

sleep 3
curl -fsS http://127.0.0.1:8000/health && echo
echo "Worker up. Lock the security group to your IP and set CLOUD_WORKER_URL / WORKER_API_KEY on your machine."
