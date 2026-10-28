#!/usr/bin/env bash
# Paste into EC2 console -> Launch instance -> Advanced details -> User data (Ubuntu 24.04 AMI).
# Replace the key below with the WORKER_API_KEY from your local .env before launching.
# The instance then builds and starts the hardened worker on port 8000 (takes ~3-5 minutes).
# Same steps as deploy/terraform/user_data.sh.tftpl; see docs/DEPLOY.md for the security group.
set -euo pipefail
export WORKER_API_KEY='PASTE-YOUR-WORKER_API_KEY-HERE'
export REPO_URL='https://github.com/Adithya-109/ai-scheduler-aws.git'
export BRANCH='improve/continuation'
apt-get update -y && apt-get install -y git curl
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" /opt/ai-scheduler-aws
install -m 0755 /opt/ai-scheduler-aws/deploy/ec2_setup.sh /home/ubuntu/ec2_setup.sh
chown ubuntu:ubuntu /home/ubuntu/ec2_setup.sh
sudo -u ubuntu --preserve-env=WORKER_API_KEY,REPO_URL,BRANCH bash /home/ubuntu/ec2_setup.sh
