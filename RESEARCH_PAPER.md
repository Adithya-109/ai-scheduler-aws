# Intelligent Cloud-Edge Workload Orchestration via Static AST Cost Estimation and Live Network Measurement

**Authors:** Adithya Binoj Nair  
**Affiliation:** Department of Computer Science and Engineering, School of Computer Science and Engineering, Vellore Institute of Technology (VIT)  
**Course Context:** Cloud Computing (CAD) Project Work  

> **Status of this draft.** Every number below is produced by code in this repository and can be regenerated with `python3 train_model.py` and `python3 bench/run_benchmarks.py` (tables in `bench/RESULTS.md`, raw output in `bench/results.json`, unseen-workload run in `bench/holdout_results.json`). The first version of this paper reported 99.4% routing accuracy, R² = 0.972 and a 41.8% latency reduction; those figures did not survive an audit (Section 4.6) and have been removed. The literature survey (Section 2) is carried over unchanged from the first draft and its references have **not** been re-verified; check each citation against the source before submission.

---

## Abstract

Offloading a job from a local "edge" machine to a cloud instance only pays off when the compute time saved exceeds the network cost of sending it. We study a scheduler for Python scripts that makes this decision *before* running anything: it parses the source into an abstract syntax tree (AST), estimates the work the program will do, predicts runtime on both nodes with gradient-boosted regressors trained only on measured timings, adds a live round-trip-time (RTT) estimate and a queue penalty, and routes the job to whichever side is predicted to finish first. A hardened HTTP worker, a dispatcher with cloud-to-edge fallback and a circuit breaker, a decision log, and a retraining loop that learns from that log complete the system.

On 495 scripts with measured edge and cloud times, and with whole script families held out of training, the latency models reach R² = 0.91 (edge) and 0.89 (cloud) on log-runtime, with median absolute errors of 15% and 3%. On the same data the cloud was faster than the edge, once the 110 ms RTT is paid, for **1 of 495** scripts. The two nodes in the dataset are similar machines, so there is almost nothing to schedule: the scheduler's total time is within 3.1% of always running locally (109.3 s vs 106.0 s; oracle 105.9 s), and it cannot be shown to beat that baseline on this data. An earlier pipeline that used a classifier trained on synthetic labels sent 158 scripts to the cloud and was 35.6% *slower* than always-edge on the same scripts. On 16 hand-written scripts the generator never produced, the static complexity estimate has a Spearman rank correlation of 0.43 with measured runtime, which is useful but weak. We report these results as they are and describe the experiment (a real hardware asymmetry) that would test the claim the system is built for.

**Keywords:** computation offloading, edge-cloud scheduling, static analysis, abstract syntax tree, latency prediction, gradient boosting, out-of-fold evaluation.

---

## 1. Introduction

Edge devices run code with no network cost but limited compute; cloud instances offer more compute at the price of a wide-area round trip [1]–[6]. A script that takes 15 ms locally cannot benefit from a cloud node 110 ms away, however fast that node is. Deciding well therefore requires an estimate of how long the script will run on each side, obtained cheaply and without running untrusted code.

Prior systems profile by executing code or require annotations [7], [8], assume a fixed network cost [9], or decide by comparing two noisy runtime predictions [10]. This project asks a narrower, testable question: *can a static, execution-free cost estimate plus measured runtimes and a live RTT pick the faster node, and by how much does it beat the trivial baseline of always running locally?*

Contributions:

1. **A static cost analyser** that walks the AST and returns an estimate in log₁₀ "equivalent Python operations", with separate accounting for interpreted operations, NumPy element operations and BLAS floating-point work, per-loop bound inference with constant propagation, recursion growth, and detection of time-bound busy-wait loops (Section 3.2).
2. **A decision rule with no learned veto.** Two regressors predict log-runtime on each node from measured data only; the route follows from the inequality in Section 3.1, and the confidence reported is the probability, under the models' measured error, that the chosen side really is faster.
3. **A deployable execution layer**: authenticated, resource-limited workers, a dispatcher with fallback and circuit breaker, live RTT, queue-aware routing, runtime history, and a JSON-lines decision log from which the models are retrained (Section 3.4).
4. **An evaluation designed to be hard to fool**: out-of-fold predictions with whole script families held out, scored by the *total wall-clock time* of each policy on real measurements against the oracle, always-edge and always-cloud baselines, plus an unseen-workload holdout (Section 4).
5. **A negative result and an audit.** With the available data the scheduler does not beat always-edge, and the original headline numbers were artefacts (Section 4.6).

Section 2 surveys related work; Section 3 describes the method; Section 4 gives results; Section 5 discusses performance and limits; Section 6 concludes.

---

## 2. Literature Survey

The architecture of intelligent cloud-edge offloading lies at the intersection of distributed systems, static code analysis, and predictive machine learning. This section synthesizes the state of the art across 32 seminal and contemporary works.

### 2.1 Edge Computing and Computation Offloading Frameworks
Computation offloading originated with mobile cloud computing systems designed to conserve device battery life. Cuervo et al. [11] introduced *MAUI*, which utilized fine-grained program profiling to offload .NET methods to infrastructure servers, though requiring developer-annotated code and homogeneous runtime environments. Chun et al. [12] developed *CloneCloud*, executing partitioned application threads inside synchronized virtual machine clones in the cloud, albeit with substantial memory synchronization overhead. Kosta et al. [13] proposed *ThinkAir*, addressing scalability by provisioning on-demand cloud virtual machine workers via a lightweight client library.

Satyanarayanan [14] formalized the *Cloudlet* paradigm, establishing that physical proximity and single-hop wireless access are mandatory to achieve low-latency offloading. Mach and Becvar [15] provided a taxonomy of Mobile Edge Computing (MEC), surveying optimal decision criteria balancing energy efficiency against delay constraints. Mao et al. [16] formulated dynamic computation offloading as a Lyapunov optimization problem, establishing theoretical trade-offs between energy harvesting and execution delays. Chen et al. [17] applied game-theoretic decentralized mechanisms to resolve multi-user offloading contention in multi-channel wireless environments. Wang et al. [18] investigated dynamic service placement at the edge, demonstrating that static offload thresholds fail under stochastic request arrivals. Lin et al. [19] surveyed edge computing architectures, underscoring that network transit latency remains the dominant determinant of Quality of Service (QoS). Kumar and Lu [20] demonstrated that cloud offloading is only energy-efficient when the computational intensity per transmitted byte exceeds a strict hardware-dependent threshold. Zhang et al. [21] analyzed collaborative edge-cloud architectures, proving that distributed hierarchical coordination consistently outperforms centralized cloud dispatching.

### 2.2 Static Code Analysis and AST-based Complexity Estimation
To avoid the runtime overhead of dynamic profiling, researchers have investigated static analysis to infer software execution cost. Alon et al. [22] introduced *code2vec*, demonstrating that syntactic paths within Abstract Syntax Trees (AST) capture semantic intent and can predict method names and properties using neural path attention. Mou et al. [23] designed tree-based convolutional neural networks (TBCNN) over AST representations, proving that structural syntax tree nodes encode algorithmic execution logic superior to sequential token models. Allamanis et al. [24] surveyed machine learning applied to source code analysis, identifying that structural graph representations provide inductive biases for runtime reasoning.

Goldsmith et al. [25] developed *Measure*, an automated framework measuring empirical computational complexity by executing instrumented code over synthetic inputs. Gulwani et al. [26] developed *SPEED*, an invariant-based framework that statically bounds nested loop iterations and worst-case execution time (WCET) using symbolic algebraic relations. Nygard et al. [27] demonstrated that static analysis of control-flow graphs (CFGs) can bound loop execution times for real-time embedded systems without execution. Cito et al. [28] integrated static AST inspection into developer IDEs to warn of latency-inducing anti-patterns prior to deployment. Santos et al. [29] investigated AST structural metrics (cyclomatic complexity, nesting depth, and operational counts) to estimate computational throughput in distributed data processing jobs. Hellendoorn et al. [30] proved that hybrid models combining AST tree traversals with static token features achieve high precision in code quality and execution path inference.

### 2.3 Machine Learning & Latency Prediction in Cloud-Edge Hybrid Systems
Predicting distributed execution latency under variable hardware configurations requires data-driven statistical models. Didona et al. [31] evaluated white-box vs. black-box machine learning approaches for performance prediction in distributed computing environments, concluding that ensemble tree regressors deliver superior generalization over non-linear execution curves. Zhang et al. [32] utilized support vector regression (SVR) to forecast task completion times on heterogeneous cloud virtual machines based on task parameterization. Dinda [33] conducted pioneering work on host load and execution time prediction in computational grids, showing that statistical regression models accurately forecast short-term resource contention.

Chen and Bahsoon [34] proposed self-adaptive latency prediction models for multi-tenant cloud platforms using online regression. Li et al. [35] employed deep reinforcement learning for computation offloading in vehicular edge computing, balancing dynamic channel fading against computing deadlines. Sonmez et al. [36] introduced machine learning-based edge orchestrators that classify incoming requests into edge-friendly and cloud-friendly categories using fuzzy logic and neural estimators. Tang and He [37] demonstrated that Gradient Boosted Decision Trees (GBDT) outperform deep neural networks on tabular hardware performance benchmarks due to their robustness against input feature scale variance. Bi et al. [38] developed latency-aware offloading in 5G networks, confirming that active RTT probing significantly reduces latency estimation error. Finally, Wu et al. [39] designed predictive runtime managers for heterogeneous mobile processors, demonstrating that log-scaling execution targets resolves magnitude skew across multi-tier workload distributions.

---

## 3. Method

### 3.1 Decision rule

For a script $S$, let $\hat t_E(S)$ and $\hat t_C(S)$ be the predicted compute times on the edge and cloud nodes, $r$ the round-trip time to the cloud worker, $b$ the payload size and $B$ the uplink bandwidth, and $q_E, q_C$ queue penalties for nodes whose job slots are full. The estimated turnaround times are

$$T_E = \hat t_E + q_E, \qquad T_C = \hat t_C + r + \frac{b}{B} + q_C ,$$

and the scheduler routes to the cloud if and only if

$$T_C < T_E\,(1-m),$$

where $m \ge 0$ is an optional safety margin (default 0). This is the only decision path. An earlier design also trained a classifier whose output could veto this comparison; it was removed because its labels were synthetic (Section 4.6).

**Confidence.** With out-of-fold residual standard deviations $\sigma_E, \sigma_C$ (in log₁₀ seconds) stored at training time, the log-ratio $d=\ln T_E-\ln T_C$ is treated as normally distributed with standard deviation $s=\ln 10\sqrt{\sigma_E^2+(\sigma_C\,\hat t_C/T_C)^2}$. The reported confidence is $\Phi(d/s)$ if the cloud is chosen and $1-\Phi(d/s)$ otherwise: the probability that the chosen side is the faster one, assuming the model error is as measured. It is therefore at least 0.5 when $m=0$. This is a normal approximation, not a calibrated probability, and Section 5.4 lists it as a limitation.

### 3.2 Static cost estimation

The analyser parses the source with Python's `ast` module and never executes it. It returns thirteen features (`num_lines`, `num_loops`, `max_loop_depth`, `num_operations`, `has_heavy_lib`, `num_function_calls`, `num_comprehensions`, `has_recursion`, `time_bound_s`, `log_python_ops`, `log_numpy_elems`, `log_blas_flops`, `estimated_complexity`). The cost features are computed as follows.

* **Loop bounds.** `for i in range(n)` uses the constant bound when it can be resolved (literals, simple constant propagation, `range` arguments); nested loops multiply. An unresolvable `for` bound is assumed to run 100 iterations and an unresolvable `while` 1000. These defaults are guesses, and they are the largest known source of error (Section 4.5).
* **Log-space arithmetic.** Costs are carried as log₁₀ values and added with a log-sum-exp, so deeply nested or large-constant programs cannot overflow. The first version used `max_integer ** loop_depth` and saturated at a clamp.
* **Three cost channels.** Interpreted operations are counted as Python ops; NumPy array expressions contribute element operations; matrix products, solves and inversions contribute BLAS flops. They are kept separate because their cost per unit differs by orders of magnitude, and the regressors learn the exchange rate.
* **Comprehensions and recursion.** Comprehensions are treated as loops over their source iterable. For self-recursive functions the call-count growth rate is found by bisection on the recurrence implied by the number of self-calls per body, so `fib(n)` grows as $\varphi^n$ rather than being treated as a single call.
* **Time-bound busy-wait.** `while time.time() - t < c` is recognised and contributes a floor of $c$ seconds in `time_bound_s`, because its cost is wall-clock rather than operation count.
* **Budget.** Traversal stops after a fixed node budget; the result is flagged `analysis_degraded` rather than raising.

`estimated_complexity` is the log₁₀ of the combined operation estimate and is used for display and for the rank-correlation test in Section 4.5; the models consume the full feature vector.

### 3.3 Latency models

Two `HistGradientBoostingRegressor`s (depth 5, learning rate 0.06, early stopping on a 15% validation split) predict $\log_{10}$ runtime on the edge and on the cloud from the feature vector. Targets are **measured** times only. Predicting the log makes errors relative, which matches the decision (a ratio), and resolves the six-orders-of-magnitude spread in runtimes. Library versions are recorded in the model metadata and checked on load because scikit-learn pickles are not portable across versions.

### 3.4 Execution layer

* **Worker** (FastAPI): `X-API-Key` authentication with constant-time comparison; refuses to bind a non-loopback address without a key; runs each job in a fresh interpreter in isolated mode with a scrubbed environment, a private working directory, CPU-time and memory `rlimit`s, a wall-clock timeout, output and code size caps, and process-group kill; bounded concurrent slots with HTTP 503 when full; unauthenticated `/health` reporting active jobs and CPU count. This is *hardening, not a sandbox*: the worker still runs arbitrary code with the privileges of its user and must be deployed with the network and instance controls in `docs/DEPLOY.md`.
* **RTT.** An exponentially weighted moving average over `/health` round trips supplies $r$. Precedence: explicit setting (the UI slider), then the live estimate, then the value measured at training.
* **Dispatcher.** Runs the job on the chosen node; falls back to the edge on cloud error; opens a circuit breaker after consecutive cloud failures; optionally explores the non-chosen side with probability $\epsilon$ on low-confidence jobs so both models keep seeing data.
* **History.** If a script (by content hash) has at least two clean prior runs on a side, the observed median replaces the regression for that side and its error is taken as small ($\sigma=0.05$ log₁₀), which covers code the static analyser cannot see through.
* **Decision log and retraining.** Every dispatch appends one JSON line (features, predictions, decision, outcome, timings). `train_model.py --log` adds logged outcomes to the training set, closing the loop.

---

## 4. Results

All numbers come from `bench/RESULTS.md` (full mode; Python 3.13, scikit-learn 1.9.1, 2 CPUs) unless stated otherwise.

### 4.1 Data

The dataset is 495 scripts, each with a measured edge time and cloud time (`hardware_benchmark.csv`, the audited form of the first draft's measurements, keyed by file name; features are recomputed from the script source so labels cannot drift out of alignment). Scripts come from parameterised templates (`generate_diverse_scripts.py`) spanning loops, nested and triple loops, recursion, sorting, string and dictionary work and NumPy matrix and element-wise operations, plus a set of generated `script_NNN` programs. For grouped evaluation each hand-written template is one *family* and the roughly 450 generated programs are bucketed into eight families by index. Median runtimes are 35 ms (edge) and 17 ms (cloud); the maximum is about 10 s on both. RTT is 110 ms.

**The two nodes are similar machines.** The cloud's compute time is lower for 373 of 495 scripts, but after adding the RTT the cloud wins on 1 of 495. The dataset therefore contains almost no examples in which routing to the cloud is correct.

### 4.2 Evaluation protocol

Predictions are produced **out of fold**: 5-fold `GroupKFold` with groups equal to script family, so the model never sees a family it is scored on. For each script we then add up the wall-clock time each policy would have spent, using the measured times:

* *oracle* — the better of (edge) and (cloud + RTT) per script;
* *always edge*, *always cloud*;
* *scheduler* — the measured time of whichever side it chose.

This answers the practical question directly (is the scheduler better than not scheduling?) and does not reward accuracy on easy cases. Reporting "routing accuracy" alone is misleading here: always choosing the edge agrees with the measured winner on 494 of 495 scripts (99.8%).

### 4.3 Model quality (out of fold, families held out)

| Metric | Edge | Cloud |
| --- | ---: | ---: |
| R² on log₁₀ runtime | 0.911 | 0.889 |
| Median absolute % error | 15.3% | 2.9% |
| Residual σ (log₁₀ s) | 0.150 | 0.220 |

### 4.4 Scheduling outcome

| Policy | Total time (s) | vs always-edge |
| --- | ---: | ---: |
| Oracle | 105.9 | −0.0% |
| Always edge | 106.0 | baseline |
| **Scheduler** | **109.3** | **+3.1%** |
| Always cloud | 182.9 | +72.6% |

The scheduler sends 2 scripts to the cloud (1 is a true cloud win) and loses 3.3 s to the oracle. It does not beat always-edge; with a single cloud-favourable script in the data that outcome cannot be changed by a better model. Sensitivity to RTT behaves as expected:

| RTT | 1 ms | 10 ms | 50 ms | 110 ms | 200 ms | 500 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Routed to cloud | 74.3% | 62.3% | 1.5% | 1.4% | 1.4% | 1.4% |

No script flips from edge to cloud as RTT rises. Binning scripts by estimated complexity (eight bins, median per bin), the measured edge time is 29–45 ms for the first six bins and the cloud time plus RTT is 125–147 ms. In the heaviest bin (about 7.3 log₁₀ ops) the edge takes 0.87 s and the cloud 2.13 s including the RTT: the two curves approach but never cross in the data (Section 5.2).

### 4.5 Unseen workloads

To test the extractor on code it was not developed against, 16 scripts were written by hand (`holdout/`): a sieve, Collatz, trial-division primes, an LCS dynamic program, recursive Fibonacci, dictionary and string workloads, NumPy matrix multiply, elementwise and inverse, a large sort, a busy-wait, and a trivial `print`. Each was run three times locally (median reported, `bench/holdout.py`).

The Spearman rank correlation between `estimated_complexity` and measured runtime is **0.43** ($n=16$). This is a weak positive relation, not a good predictor, and a sample of 16 gives a wide interval. The misses are informative: loop bounds derived from `len()` of constructed strings (the LCS program) and `while` loops with a non-constant bound (trial division) fall back to the default guesses and are underestimated; NumPy workloads carry a fixed interpreter-plus-import cost of about 0.1 s that has nothing to do with problem size. The regressors, not this raw feature, drive routing, and the history mechanism (Section 3.4) exists for exactly these programs; but the held-out check of the full scheduler on unseen scripts requires real two-node measurements and has not been done.

### 4.6 Audit of the original results

The first draft reported 99.4% routing accuracy, R² = 0.972 and a 41.8% latency reduction. Re-running the original pipeline and inspecting it showed:

* the routing label was derived from an `edge_scale` factor invented in the training script (`modeled_edge_time = actual_edge_time * edge_scale`), so the classifier learned to reproduce a formula rather than a measurement, and its accuracy was scored against that same formula;
* the regressors' R² came from `cross_val_score(cv=5)` over the rows in file order, ignoring script families, with near-duplicate parameterisations of the same template free to fall on both sides of a split;
* feature values were stored in the CSV beside the timings rather than recomputed from the scripts, so any change to the extractor left stale features, and rows carried no file name;
* on the shipped data the old pipeline routed 158 scripts to the cloud and took 143.7 s, **35.6% slower** than always-edge (106.0 s);
* the old and new R² (0.972 vs 0.91/0.89) are not comparable: they use different features, a different target construction and, crucially, different splits.

The corrected pipeline routes 2 scripts to the cloud and takes 109.3 s (+3.1%). Reproduction: `python3 bench/run_benchmarks.py` (the "before vs after" table) and `tests/test_audit.py`.

### 4.7 Overheads and execution layer

| Step | p50 | p95 |
| --- | ---: | ---: |
| AST feature extraction | 0.63 ms | 1.06 ms |
| Full `schedule()` call (features + both models + rule) | 3.56 ms | 5.29 ms |
| Model cold load | 20 ms | — |
| Interpreter spawn per job | 17.7 ms | — |

The first draft claimed extraction "in under 12 ms"; it is about 0.6 ms. A concurrency test against a local worker over real sockets (40 requests, 2 CPUs) completes 14, 26 and 27 requests at 1, 2 and 4 slots and returns HTTP 503 for the rest instead of queueing without bound. The FastAPI front end could not be installed in the audit environment; the same wire contract is exercised through a stdlib server around the identical runner code, and the repository's test suite passes.

---

## 5. Performance, limits and what remains

### 5.1 Comparison with the baselines

On the data available, the ranking is oracle ≈ always-edge < scheduler < always-cloud. The scheduler's value on this data is that it **avoids the 72.6% penalty of always-cloud** and the 35.6% penalty of the original design while staying within 3.1% of the best fixed policy. It does not demonstrate a gain over running locally.

### 5.2 Where offloading would pay

For a job with edge time $t_E$ and cloud time $t_C$, offloading helps when $t_E - t_C > r + b/B$. At $r=110$ ms the cloud must save more than 110 ms of compute, so no job faster than about 0.1 s on the edge can ever benefit. In the dataset the heaviest jobs take about the same time on both nodes (maxima of about 10 s each), so even among long jobs the cloud saves almost nothing; only one script clears the bar. A cloud node with several times the edge's compute (more cores for BLAS, a faster CPU) would pull the break-even down towards jobs of a few hundred milliseconds. This is a prediction of the model, to be tested, not a measured result.

### 5.3 Experiment needed to test the claim

1. Make the nodes genuinely different (`docs/DEPLOY.md`: for example a throttled local worker versus a multi-core instance).
2. Re-collect with `collect_data.py` (repeated runs, spread and failures recorded, hardware metadata stored), retrain with `train_model.py --probe`, and re-run `bench/run_benchmarks.py`.
3. Report scheduler vs always-edge, always-cloud and oracle with families held out, as in Section 4.2.

### 5.4 Limitations and threats to validity

* **No hardware asymmetry in the data** (above). This is the dominant limitation.
* **Template-generated workloads.** Holding out families reduces leakage, but the families are still one author's templates; the 16-script holdout is small and has no cloud measurements.
* **Static-analysis blind spots.** Data-dependent loop bounds, `exec`/`eval`, I/O and library calls with input-dependent cost are invisible to the analyser. History and retraining from the log are mitigations, not a proof of coverage.
* **Single run conditions.** RTT was measured to a single region; network jitter, cold starts and CPU contention on a shared instance are only modelled through the EWMA and the queue heuristic.
* **Confidence is approximate.** It assumes normal, homoscedastic log-errors.
* **Security.** The worker is hardened, not sandboxed. The first draft's EC2 address and security-group identifiers appeared in the repository history; the address has been redacted in the current tree but remains in earlier commits, so the instance should be rotated or locked down.
* **Terraform** in `deploy/terraform` encodes the intended network posture but has not been applied or validated with a Terraform binary.

---

## 6. Conclusion

We built and audited an execution-free scheduler for Python jobs. Static AST cost features and gradient-boosted regressors trained only on measured runtimes predict edge and cloud time to R² of 0.91 and 0.89 with whole script families held out, and a single transparent inequality over those predictions, a live RTT estimate and a queue penalty makes the routing decision. The surrounding system (authenticated, limited workers; fallback and circuit breaking; runtime history; a decision log that feeds retraining) is tested end to end.

The main finding is a negative one. On 495 measured scripts the cloud wins once, so the scheduler ends within 3.1% of always-edge and cannot be shown to improve on it, while the original design's headline numbers (99.4% accuracy, 41.8% latency reduction) came from synthetic labels and leaky evaluation and were in fact a 35.6% slowdown. Whether the approach delivers a real benefit depends on running it where the cloud node is substantively faster than the edge, and the repository now contains the tooling, protocol and baselines to do exactly that.

**Future work.** Run the asymmetric-hardware experiment; evaluate the full scheduler on unseen workloads with two-node measurements; extend the analyser to infer bounds from `len()` and simple data flow; calibrate the confidence on logged outcomes; and consider migrating packages or containers rather than single scripts.

---

## References

[1] W. Shi, J. Cao, Q. Zhang, Y. Li, and L. Xu, "Edge computing: Vision and challenges," *IEEE Internet of Things Journal*, vol. 3, no. 5, pp. 637–646, Oct. 2016.  
[2] F. Bonomi, R. Milito, J. Zhu, and S. Addepalli, "Fog computing and its role in the Internet of Things," in *Proc. 1st Edition of the MCC Workshop on Mobile Cloud Comput.*, Helsinki, Finland, 2012, pp. 13–16.  
[3] M. Satyanarayanan, "The emergence of edge computing," *Computer*, vol. 50, no. 1, pp. 30–39, Jan. 2017.  
[4] Y. Mao, C. You, J. Zhang, K. Huang, and K. B. Letaief, "A survey on mobile edge computing: The communication perspective," *IEEE Communications Surveys & Tutorials*, vol. 19, no. 4, pp. 2322–2358, 4th Quart., 2017.  
[5] M. Armbrust, A. Fox, R. Griffith, A. D. Joseph, R. Katz, A. Konwinski, G. Lee, D. Patterson, A. Rabkin, I. Stoica, and M. Zaharia, "A view of cloud computing," *Communications of the ACM*, vol. 53, no. 4, pp. 50–58, Apr. 2010.  
[6] P. Mach and Z. Becvar, "Mobile edge computing: A survey on architecture and computation offloading," *IEEE Communications Surveys & Tutorials*, vol. 19, no. 3, pp. 1628–1656, 3rd Quart., 2017.  
[7] C. Wang, C. Liang, F. R. Yu, Q. Chen, and L. Tang, "Computation offloading and resource allocation in wireless cellular networks with mobile edge computing," *IEEE Transactions on Wireless Communications*, vol. 16, no. 8, pp. 4924–4938, Aug. 2017.  
[8] X. Chen, L. Jiao, W. Li, and X. Fu, "Efficient multi-user computation offloading for mobile-edge cloud computing," *IEEE/ACM Transactions on Networking*, vol. 24, no. 5, pp. 2795–2808, Oct. 2016.  
[9] S. Deng, L. Huang, J. Taheri, and A. Y. Zomaya, "Computation offloading for service workflow in mobile cloud computing," *IEEE Transactions on Parallel and Distributed Systems*, vol. 26, no. 12, pp. 3317–3329, Dec. 2015.  
[10] D. Didona, P. Felber, and D. R. K. Ports, "Performance modeling of distributed systems using machine learning," in *Proc. IEEE 35th Int. Conf. on Distrib. Comput. Syst. (ICDCS)*, Columbus, OH, USA, 2015, pp. 640–651.  
[11] E. Cuervo, A. Balasubramanian, D. Cho, A. Wolman, S. Saroiu, R. Chandra, and P. Bahl, "MAUI: Making smartphones last longer with code offload," in *Proc. 8th Int. Conf. on Mobile Syst., Appl., and Services (MobiSys)*, San Francisco, CA, USA, 2010, pp. 49–62.  
[12] B.-G. Chun, S. Ihm, P. Maniatis, M. Naik, and A. Patti, "CloneCloud: Elastic execution between mobile device and cloud," in *Proc. 6th Conf. on Comput. Syst. (EuroSys)*, Salzburg, Austria, 2011, pp. 301–314.  
[13] S. Kosta, A. Aucinas, P. Hui, R. Mortier, and X. Zhang, "ThinkAir: Dynamic resource allocation and on-demand execution for mobile cloud computing," in *Proc. IEEE INFOCOM*, Orlando, FL, USA, 2012, pp. 945–953.  
[14] M. Satyanarayanan, P. Bahl, R. Caceres, and N. Davies, "The case for VM-based cloudlets in mobile computing," *IEEE Pervasive Computing*, vol. 8, no. 4, pp. 14–23, Oct.–Dec. 2009.  
[15] Z. Sanaei, S. Abolfazli, A. Gani, and R. Buyya, "Heterogeneity in mobile cloud computing: Taxonomy and open challenges," *IEEE Communications Surveys & Tutorials*, vol. 16, no. 1, pp. 369–392, 1st Quart., 2014.  
[16] Y. Mao, J. Zhang, and K. B. Letaief, "Dynamic computation offloading for mobile-edge computing with energy harvesting devices," *IEEE Journal on Selected Areas in Communications*, vol. 34, no. 12, pp. 3590–3605, Dec. 2016.  
[17] X. Chen, "Decentralized computation offloading game for mobile cloud computing," *IEEE Transactions on Parallel and Distributed Systems*, vol. 26, no. 4, pp. 974–983, Apr. 2015.  
[18] S. Wang, R. Urgaonkar, M. Zafer, T. He, K. Chan, and K. K. Leung, "Dynamic service placement for mobile micro-clouds with filtering," *IEEE/ACM Transactions on Networking*, vol. 25, no. 2, pp. 1007–1020, Apr. 2017.  
[19] J. Lin, W. Yu, N. Zhang, X. Yang, H. Zhang, and W. Zhao, "A survey on internet of things: Architecture, enabling technologies, security and privacy, and applications," *IEEE Internet of Things Journal*, vol. 4, no. 5, pp. 1125–1142, Oct. 2017.  
[20] K. Kumar and Y.-H. Lu, "Cloud computing for mobile users: Can offloading computation save energy?," *Computer*, vol. 43, no. 4, pp. 51–56, Apr. 2010.  
[21] K. Zhang, Y. Mao, S. Leng, Y. He, and Y. Zhang, "Mobile-edge computing for energy-constrained mobile devices in 5G wireless networks," *IEEE Communications Magazine*, vol. 54, no. 12, pp. 18–24, Dec. 2016.  
[22] U. Alon, M. Zilberstein, O. Levy, and E. Yahav, "code2vec: Learning distributed representations of code," *Proc. ACM Program. Lang.*, vol. 3, no. POPL, pp. 1–29, Jan. 2019.  
[23] L. Mou, G. Li, L. Zhang, T. Wang, and Z. Jin, "Convolutional neural networks over tree structures for programming language processing," in *Proc. 30th AAAI Conf. on Artif. Intell. (AAAI)*, Phoenix, AZ, USA, 2016, pp. 1287–1293.  
[24] M. Allamanis, E. T. Barr, P. Devanbu, and C. Sutton, "A survey of machine learning for big code and naturalness," *ACM Computing Surveys*, vol. 51, no. 4, pp. 1–37, Jul. 2018.  
[25] S. F. Goldsmith, A. S. Aiken, and D. S. Wilkerson, "Measuring empirical computational complexity," in *Proc. 6th Joint Meet. of the Eur. Softw. Eng. Conf. and the ACM SIGSOFT Symp. on the Found. of Softw. Eng. (ESEC/FSE)*, Dubrovnik, Croatia, 2007, pp. 395–404.  
[26] S. Gulwani, K. K. Mehra, and T. Chilimbi, "SPEED: Symbolic complexity bound analysis," in *Proc. 36th ACM SIGPLAN-SIGACT Symp. on Princ. of Program. Lang. (POPL)*, Savannah, GA, USA, 2009, pp. 127–140.  
[27] M. Nygard, P. Lokuciejewski, and H. Falk, "Static WCET analysis based loop bounds computation for embedded real-time systems," in *Proc. 14th IEEE Int. Conf. on Embedded Real-Time Comput. Syst. and Appl. (RTCSA)*, Kaohsiung, Taiwan, 2008, pp. 347–356.  
[28] J. Cito, P. Leitner, H. C. Gall, and M. Pezzè, "Feedback-driven development: Integrating developer IDEs with runtime performance insights," in *Proc. 39th Int. Conf. on Softw. Eng. (ICSE)*, Buenos Aires, Argentina, 2017, pp. 343–353.  
[29] E. Santos and M. Hindle, "Judging a commit by its cover: Correlating commit complexity metrics with build and runtime costs," *Information and Software Technology*, vol. 79, pp. 74–88, Nov. 2016.  
[30] V. J. Hellendoorn, C. Bird, E. T. Barr, and P. Devanbu, "Deep learning type inference: What will it take?," in *Proc. IEEE/ACM 40th Int. Conf. on Softw. Eng. (ICSE)*, Gothenburg, Sweden, 2018, pp. 152–162.  
[31] D. Didona and P. Romano, "Tuning transactional memory via black-box and white-box machine learning models," *IEEE Transactions on Parallel and Distributed Systems*, vol. 26, no. 6, pp. 1561–1572, Jun. 2015.  
[32] Y. Zhang, W. Sun, and Y. Dey, "Automated workload execution time prediction on heterogeneous cloud servers using support vector machines," *IEEE Transactions on Services Computing*, vol. 12, no. 3, pp. 412–425, May–Jun. 2019.  
[33] P. A. Dinda, "Online prediction of the running time of tasks," *Cluster Computing*, vol. 5, no. 3, pp. 225–236, Jul. 2002.  
[34] T. Chen and R. Bahsoon, "Self-adaptive latency trade-off modeling for cloud service compositions using online regression," *IEEE Transactions on Software Engineering*, vol. 43, no. 5, pp. 489–507, May 2017.  
[35] X. Li, J. Wan, H. Dai, M. Imran, M. Xia, and M. Celesti, "A deep reinforcement learning approach for computation offloading in vehicular edge computing," *ACM Transactions on Intelligent Systems and Technology*, vol. 12, no. 1, pp. 1–22, Jan. 2021.  
[36] C. Sonmez, A. Ozgovde, and C. Ersoy, "Fuzzy active queue management for edge-cloud collaborative scheduling," *IEEE Transactions on Cloud Computing*, vol. 9, no. 4, pp. 1572–1585, Oct.–Dec. 2021.  
[37] M. Tang and W. He, "Predictive performance modeling on cloud micro-benchmarks: GBDT versus Deep Neural Networks," *IEEE Transactions on Cloud Computing*, vol. 10, no. 2, pp. 910–924, Apr.–Jun. 2022.  
[38] S. Bi, L. Huang, H. Wang, and Y. A. Zhang, "Computation offloading and resource allocation in wireless powered mobile edge computing," *IEEE Transactions on Wireless Communications*, vol. 17, no. 8, pp. 5341–5355, Aug. 2018.  
[39] C. Wu, X. Zhou, and H. Wang, "Predictive energy-latency management on heterogeneous processors via logarithmic target regression," *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, vol. 39, no. 11, pp. 3840–3852, Nov. 2020.  
