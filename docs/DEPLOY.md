# Deploying the worker (and getting a real edge/cloud difference)

The worker executes arbitrary Python it is sent. Treat the cloud node as
disposable and assume anything on it can be read by whoever can reach port 8000.

## 1. Network first

| Setting | Value | Why |
| --- | --- | --- |
| Security group, inbound 8000 | **your IP only** (or no inbound, and use an SSH tunnel / VPN) | The API key is a second lock, not the first |
| Security group, outbound | deny all except what you need (DNS/NTP, package mirrors during setup) | Submitted code can't call out or exfiltrate |
| Instance role | **none** | Nothing for submitted code to steal |
| IMDS | IMDSv2 required, hop limit 1 (`aws ec2 modify-instance-metadata-options --instance-id i-… --http-tokens required --http-put-response-hop-limit 1`) | A container can't reach instance credentials |
| TLS | terminate at a reverse proxy, or tunnel (`ssh -L 8000:localhost:8000 …`) | The API key and code travel in clear text over plain HTTP |

**The previous version of this repo committed the instance's public IP in
`app.py`, `collect_data.py` and `train_model.py`, and the worker had no
authentication.** The IP is still in git history. Until you have done the
steps above, stop the instance, or release/replace its Elastic IP.

## 2. Run the worker

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # -> WORKER_API_KEY
# on the instance (Ubuntu):
WORKER_API_KEY=<key> REPO_URL=https://github.com/<you>/ai-scheduler-aws.git bash deploy/ec2_setup.sh
```

The container runs as a non-root user, read-only root filesystem, all
capabilities dropped, `no-new-privileges`, a PID limit, and per-job rlimits
(memory, CPU seconds, file size) plus a wall-clock timeout that kills the whole
process group. These reduce the blast radius; they are not a sandbox. Anything
that needs stronger isolation (gVisor, Firecracker, a throwaway VM per job) is
out of scope here.

Locally: `cp .env.example .env`, fill in `WORKER_API_KEY` and `CLOUD_WORKER_URL`,
then `docker compose up --build` (or `python worker/worker_server.py`, which
binds to 127.0.0.1 unless `WORKER_HOST` is set).

## 3. Make the nodes actually different

On the measured data the cloud only beat the edge on 1 of 495 scripts because
the two machines are about equally fast, so a 110 ms network penalty can almost
never be paid back. To give the scheduler something to learn, make the
difference real:

* **Weak edge:** a Raspberry Pi / old laptop, or throttle the local container:
  `EDGE_CPUS=0.5 EDGE_MEM=512m docker compose up --build`.
* **Strong cloud:** a compute-optimised multi-core instance (c-family) with
  `WORKER_MAX_JOBS` = its vCPU count; for GPU/torch workloads a g-family
  instance and torch jobs in `test_scripts/`.
* **Realistic jobs:** add scripts that read real input (pandas groupby, a
  scikit-learn fit, image resizing), so payload transfer is part of the decision.

## 4. Re-collect, retrain, check

```bash
export CLOUD_WORKER_URL=http://<host>:8000 WORKER_API_KEY=<key>
export EDGE_DESCRIPTION="Raspberry Pi 4, 4 GB" CLOUD_INSTANCE_TYPE=c7i.2xlarge
python3 collect_data.py --repeats 5            # hardware_benchmark.csv + .meta.json
python3 train_model.py --probe                 # measures RTT, prints held-out policy totals
python3 -m unittest discover -s tests -t .     # quality gates read models/training_metadata.json
python3 bench/run_benchmarks.py                # regenerates bench/RESULTS.md
```

`train_model.py` prints total wall-clock time for oracle / always-edge /
always-cloud / scheduler on held-out script families. If the scheduler does not
beat always-edge on a setup like this, that is the finding to report.

To learn from live use, run the dispatcher (`pipeline/dispatcher.py`) with a
`DecisionLog`, then `python3 train_model.py --log logs/decisions.jsonl`.
`Dispatcher(epsilon=0.05)` explores the other side on low-confidence jobs so the
log contains outcomes for both nodes.

## 5. Terraform (optional)

`deploy/terraform/` creates the worker with the settings that matter: a security
group open on 8000 to **one CIDR only** (`allowed_cidr` has no default and
rejects `0.0.0.0/0`), no SSH unless you pass `key_name`, egress limited to
HTTPS/DNS, IMDSv2 required with hop limit 1, **no instance role**, an encrypted
root volume, and user-data that runs `deploy/ec2_setup.sh` (the hardened
container).

```bash
cd deploy/terraform
cp terraform.tfvars.example terraform.tfvars   # edit: your IP, a 32+ char key, repo URL
terraform init && terraform apply
# then put the printed cloud_worker_url and the same key into .env
```

Status: this config has **not** been run through `terraform validate` or
applied (no Terraform binary was available where it was written). The static
guards in `tests/test_terraform.py` pin the security posture, but run
`terraform validate && terraform plan` before trusting it. The API key lands in
Terraform state and instance user-data: keep state private (a remote encrypted
backend) and rotate the key if either leaks. Traffic on 8000 is plain HTTP; put
TLS in front before sending anything you would not want read on the wire.

## 6. Container experiment (two workers on one machine)

No cloud account needed: `scripts/run_asymmetric_experiment.sh` runs a CPU-limited edge worker and a larger
"cloud" worker in Docker, times every script through both, and scores the scheduler out of fold. The network
delay is a simulated constant, so this tests compute asymmetry only, not your WAN.

```bash
MODE=docker EDGE_CPUS=0.5 CLOUD_CPUS=4 REPEATS=3 ./scripts/run_asymmetric_experiment.sh
# only the heavy, multi-core-friendly workloads (generate_heavy_scripts.py):
MODE=docker ONLY="blas*,fftbig*,ewisebig*,cpuloop*" EDGE_CPUS=0.5 CLOUD_CPUS=4 REPEATS=3 \
  ./scripts/run_asymmetric_experiment.sh
# merge a later run into the dataset (same hardware settings only), retrain, score with error bars:
python3 scripts/merge_datasets.py data/docker_asym_v1 experiments/<timestamp> --out data/docker_asym_v2
python3 train_model.py --data data/docker_asym_v2/asym_benchmark.csv --out-dir models/asym_v2 --rtt-ms 110
python3 bench/asym_report.py data/docker_asym_v2/asym_benchmark.csv --rtt-ms 110 --bootstrap 2000 \
  --markdown bench/ASYM_RESULTS.md
SCHEDULER_MODELS_DIR=models/asym_v2 streamlit run app.py     # run the app with those models
```

Give Docker Desktop at least as many CPUs as `CLOUD_CPUS` (Settings, Resources) and keep the machine otherwise idle
while it runs. If `docker` is not found in Terminal, add `/Applications/Docker.app/Contents/Resources/bin` to `PATH`.
