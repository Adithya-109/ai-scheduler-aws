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

## Not done (needs hardware, an account, or a decision)

* **A real edge/cloud asymmetry and a re-collected dataset.** `hardware_benchmark.csv` is the migrated v1 data (495 rows).
  `collect_data.py` and `docs/DEPLOY.md` are ready; running them needs your machines. Until then the scheduler is, correctly,
  within ~3% of always-edge and cannot be shown to beat it.
* **Terraform / full IaC** for the EC2 node (a setup script and a written checklist exist instead).
* **Rotating the exposed EC2 address.** The IP is in git history of `main`.
* **Splitting `app.py`** into pages. Left as is: no Streamlit runtime was available here to verify a refactor visually.
* **Regenerating `RESEARCH_PAPER.md` / the journal `.docx`.** Flagged with a note; the numbers need rewriting once real data exists.
* **FastAPI HTTP layer is untested directly** (not installable in the audit sandbox); covered by an equivalent stdlib server.
