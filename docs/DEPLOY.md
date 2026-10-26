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
