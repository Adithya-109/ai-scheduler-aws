# Overhaul status

Work done on branch `improve/scheduler-overhaul`, against the audit plan.
Numbers are in `bench/RESULTS.md`; the audit's baseline run is
`bench/results_audit_baseline.json`.

## Done

| Phase | Change | Evidence |
| --- | --- | --- |
| 0 Security | Worker needs `X-API-Key`, refuses non-loopback bind without one, rlimits, scrubbed env, private cwd, process-group kill, output/code caps, `/health`, bounded concurrency (503 when busy) | `tests/test_system.py` (runner + HTTP) |
| 0 Security | EC2 IP and key moved to env / `.env`; removed from `app.py`, `collect_data.py`, `train_model.py` | `test_no_hardcoded_ip` |
| 1 Data | Dataset keyed by filename; features recomputed from scripts; collector records repeats, spread, failures, hardware metadata and drops failed runs | `collect_data.py`, `tests/test_system.py::TestCollectData` |
| 1 Data | Synthetic `edge_scale` label and the classifier deleted; training uses measured times only | `test_no_synthetic_labels_in_training` |
| 2 Evaluation | Out-of-fold, whole-family evaluation; policy totals vs oracle / always-edge / always-cloud; before/after on identical scripts | `train_model.py`, `bench/` |
| 2 Evaluation | CI workflow (lint, tests, quick bench); README and UI numbers computed, not typed | `.github/workflows/ci.yml`, `pipeline/reporting.py` |
| 3 Extractor | Log-space, per-loop bounds, comprehension/recursion/NumPy/time-bound handling; no overflow; dotted imports | `tests/test_extractor.py` |
| 4 Decision | Single routing rule (no classifier veto); confidence = P(chosen side faster); live RTT; queue-aware; transfer time; margin; circuit breaker; fallback; decision log; epsilon exploration; retrain from log | `tests/test_models.py`, `test_system.py` |
| 4 Speed | `schedule()` 13.7 ms -> ~3.6 ms (two early-stopped models, no DataFrame) | `bench/RESULTS.md` |
| 5 Engineering | Pinned requirements, version recorded in model metadata and checked on load, `pyproject.toml`, ruff, Dockerfile, compose, EC2 script, UI scheduler/data caching, one-off patch scripts deleted | |

## Continuation (`improve/continuation`)

| Change | Evidence |
| --- | --- |
| Unseen-workload holdout: 16 hand-written scripts, measured locally; Spearman(complexity, runtime) = 0.43 | `bench/holdout.py`, `bench/holdout_results.json`, `tests/test_holdout.py` |
| Runtime-history fallback keyed by code hash; the dispatcher learns from its own runs | `pipeline/history.py`, `tests/test_history.py`, `tests/test_system.py` |
| `app.py` (1370 lines) split into `ui/` (theme, header, execution, four pages); linted | `tests/test_app_smoke.py` |
| UI executes through `Dispatcher` (fallback, breaker, live RTT, history, log); Telemetry tab shows the live decision log | `pipeline/reporting.py::live_log_summary`, tests |
| Terraform for a locked-down EC2 worker (single-CIDR ingress, IMDSv2 hop limit 1, no instance role, encrypted disk) | `deploy/terraform/`, `tests/test_terraform.py` (static only) |
| Docker asymmetric experiment (0.5-CPU edge vs 4-CPU cloud worker): 591 scripts timed; scheduler -6.9% vs always-edge, bootstrap 95% CI [-10.8%, -3.8%] | `data/docker_asym_v1/`, `models/asym/`, `bench/ASYM_RESULTS.md`, `tests/test_asym.py` |
| Extractor sizes arrays created by a NumPy `Generator` (`rng.random((n, n))`); no change to any existing training feature | `tests/test_extractor.py::TestGeneratorSizes` |
| 42 heavy multi-core-friendly workloads, comma-separated `--only`, dataset merge tool that refuses mixed hardware | `generate_heavy_scripts.py`, `scripts/merge_datasets.py`, `tests/test_heavy_scripts.py` |
| `RESEARCH_PAPER.md` rewritten with the audited numbers and limitations; `.docx` rebuilt from it with pandoc | `scripts/build_docx.sh` |

## Not done (needs hardware, an account, or a decision)

* **Measurements on real cloud hardware.** The container experiment (one run, simulated 110 ms delay, one machine) shows a
  6.9% gain; it does not replace a real instance. Also still to do: repeat it, and measure the 42 new heavy scripts
  (`ONLY='blas*,fftbig*,ewisebig*,cpuloop*'`, see docs/DEPLOY.md) and merge them in.
  The migrated `hardware_benchmark.csv` (495 rows, similar machines) remains the default dataset.
* **Validating the Terraform** (`terraform validate` / `plan` / `apply`): no binary was available.
* **Rotating the exposed EC2 address.** The IP is in git history of `main`; stop or lock down that instance.
* **Verifying the paper's references.** Carried over unchanged; several citations look doubtful (for example [29], [30] and
  [36]-[39] do not obviously support the claims attributed to them). Check each against the source.
* **Equations in the `.docx`** are native Word equations; they could not be previewed here (no LibreOffice Math).
* **A live Streamlit session** was never run; the UI is covered by the fake-Streamlit tests.
* **FastAPI HTTP layer is untested directly** (not installable in the audit sandbox); covered by an equivalent stdlib server.
