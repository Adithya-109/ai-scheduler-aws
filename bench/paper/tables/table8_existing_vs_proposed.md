**Similar hardware** (495 scripts)

| Metric | Edge-only | Cloud-only | A: Static threshold | B: Pure regression (two GBT regressors) | Proposed AI Scheduler |
| --- | ---: | ---: | ---: | ---: | ---: |
| Routing accuracy | 99.8 % | 0.2 % | 99.8 % | 99.4 % | **99.8 %** |
| Precision (cloud offload) | 0.0 % | 0.2 % | 0.0 % | 0.0 % | **0.0 %** |
| Recall (cloud offload) | 0.0 % | 100.0 % | 0.0 % | 0.0 % | **0.0 %** |
| F1-score | 0.000 | 0.004 | 0.000 | 0.000 | **0.000** |
| MCC | 0.000 | 0.000 | 0.000 | -0.003 | **0.000** |
| Misrouting rate | 0.2 % | 99.8 % | 0.2 % | 0.6 % | **0.2 %** |
| Decision overhead | 0.00 ms | 0.00 ms | 0.18 ms | 12.95 ms | **5.19 ms** |
| Mean turnaround per job | 0.214 s | 0.370 s | 0.214 s | 0.221 s | **0.214 s** |
| Mean turnaround reduction vs edge-only | +0.0 % | -72.6 % | +0.0 % | -3.1 % | **+0.0 %** |

**Asymmetric (591)** (591 scripts)

| Metric | Edge-only | Cloud-only | A: Static threshold | B: Pure regression (two GBT regressors) | Proposed AI Scheduler |
| --- | ---: | ---: | ---: | ---: | ---: |
| Routing accuracy | 89.7 % | 10.3 % | 87.1 % | 93.2 % | **95.8 %** |
| Precision (cloud offload) | 0.0 % | 10.3 % | 43.4 % | 74.4 % | **80.0 %** |
| Recall (cloud offload) | 0.0 % | 100.0 % | 80.3 % | 52.5 % | **78.7 %** |
| F1-score | 0.000 | 0.187 | 0.563 | 0.615 | **0.793** |
| MCC | 0.000 | 0.000 | 0.528 | 0.590 | **0.770** |
| Misrouting rate | 10.3 % | 89.7 % | 12.9 % | 6.8 % | **4.2 %** |
| Decision overhead | 0.00 ms | 0.00 ms | 0.18 ms | 12.95 ms | **5.19 ms** |
| Mean turnaround per job | 0.463 s | 0.492 s | 0.413 s | 0.431 s | **0.406 s** |
| Mean turnaround reduction vs edge-only | +0.0 % | -6.4 % | +10.8 % | +6.9 % | **+12.4 %** |

**Asymmetric + heavy (633)** (633 scripts)

| Metric | Edge-only | Cloud-only | A: Static threshold | B: Pure regression (two GBT regressors) | Proposed AI Scheduler |
| --- | ---: | ---: | ---: | ---: | ---: |
| Routing accuracy | 84.4 % | 15.6 % | 87.2 % | 96.2 % | **96.5 %** |
| Precision (cloud offload) | 0.0 % | 15.6 % | 55.6 % | 90.3 % | **89.7 %** |
| Recall (cloud offload) | 0.0 % | 100.0 % | 90.9 % | 84.8 % | **87.9 %** |
| F1-score | 0.000 | 0.270 | 0.690 | 0.875 | **0.888** |
| MCC | 0.000 | 0.000 | 0.644 | 0.853 | **0.867** |
| Misrouting rate | 15.6 % | 84.4 % | 12.8 % | 3.8 % | **3.5 %** |
| Decision overhead | 0.00 ms | 0.00 ms | 0.18 ms | 12.95 ms | **5.19 ms** |
| Mean turnaround per job | 0.549 s | 0.499 s | 0.426 s | 0.418 s | **0.417 s** |
| Mean turnaround reduction vs edge-only | +0.0 % | +9.1 % | +22.3 % | +23.9 % | **+24.1 %** |

**Real EC2 c7i-flex.large** (633 scripts)

| Metric | Edge-only | Cloud-only | A: Static threshold | B: Pure regression (two GBT regressors) | Proposed AI Scheduler |
| --- | ---: | ---: | ---: | ---: | ---: |
| Routing accuracy | 87.0 % | 13.0 % | 85.3 % | 95.9 % | **95.6 %** |
| Precision (cloud offload) | 0.0 % | 13.0 % | 46.5 % | 79.2 % | **80.0 %** |
| Recall (cloud offload) | 0.0 % | 100.0 % | 87.8 % | 92.7 % | **87.8 %** |
| F1-score | 0.000 | 0.229 | 0.608 | 0.854 | **0.837** |
| MCC | 0.000 | 0.000 | 0.568 | 0.834 | **0.813** |
| Misrouting rate | 13.0 % | 87.0 % | 14.7 % | 4.1 % | **4.4 %** |
| Decision overhead | 0.00 ms | 0.00 ms | 0.18 ms | 12.95 ms | **5.19 ms** |
| Mean turnaround per job | 0.578 s | 0.616 s | 0.469 s | 0.442 s | **0.444 s** |
| Mean turnaround reduction vs edge-only | +0.0 % | -6.6 % | +18.9 % | +23.5 % | **+23.2 %** |

