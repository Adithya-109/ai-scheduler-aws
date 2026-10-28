| Dataset | Policy | Total (s) | Mean (s) | p95 (s) | vs Edge-only | vs Cloud-only | Regret vs oracle | Routed to cloud | Decision acc. |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Similar hardware | Edge-only | 106.0 | 0.214 | 2.026 | +0.0% | -42.1% | +0.0% | 0 | 99.8% |
| Similar hardware | Cloud-only | 182.9 | 0.370 | 2.125 | +72.6% | +0.0% | +72.7% | 495 | 0.2% |
| Similar hardware | Random (p=0.5) | 144.4 | 0.292 | 2.037 | +36.2% | -21.1% | +36.3% | 248 | 50.0% |
| Similar hardware | Static threshold | 106.0 | 0.214 | 2.026 | +0.0% | -42.1% | +0.0% | 0 | 99.8% |
| Similar hardware | **AI Scheduler** | 106.0 | 0.214 | 2.026 | +0.0% | -42.1% | +0.0% | 0 | 99.8% |
| Similar hardware | Oracle (bound) | 105.9 | 0.214 | 2.026 | -0.0% | -42.1% | +0.0% | 1 | 100.0% |
| Asymmetric (591) | Edge-only | 273.7 | 0.463 | 2.076 | +0.0% | -6.0% | +15.1% | 0 | 89.7% |
| Asymmetric (591) | Cloud-only | 291.1 | 0.492 | 2.126 | +6.4% | +0.0% | +22.4% | 591 | 10.3% |
| Asymmetric (591) | Random (p=0.5) | 282.3 | 0.478 | 2.125 | +3.2% | -3.0% | +18.7% | 295 | 50.1% |
| Asymmetric (591) | Static threshold | 244.1 | 0.413 | 2.126 | -10.8% | -16.1% | +2.6% | 113 | 87.1% |
| Asymmetric (591) | **AI Scheduler** | 239.7 | 0.406 | 2.017 | -12.4% | -17.6% | +0.8% | 60 | 95.8% |
| Asymmetric (591) | Oracle (bound) | 237.8 | 0.402 | 2.017 | -13.1% | -18.3% | +0.0% | 61 | 100.0% |
| Asymmetric + heavy (633) | Edge-only | 347.5 | 0.549 | 2.217 | +0.0% | +10.0% | +32.2% | 0 | 84.4% |
| Asymmetric + heavy (633) | Cloud-only | 316.0 | 0.499 | 2.126 | -9.1% | +0.0% | +20.3% | 633 | 15.6% |
| Asymmetric + heavy (633) | Random (p=0.5) | 331.8 | 0.524 | 2.127 | -4.5% | +5.0% | +26.3% | 317 | 50.0% |
| Asymmetric + heavy (633) | Static threshold | 269.9 | 0.426 | 2.126 | -22.3% | -14.6% | +2.7% | 162 | 87.2% |
| Asymmetric + heavy (633) | **AI Scheduler** | 263.7 | 0.417 | 2.017 | -24.1% | -16.6% | +0.3% | 97 | 96.5% |
| Asymmetric + heavy (633) | Oracle (bound) | 262.8 | 0.415 | 2.017 | -24.4% | -16.8% | +0.0% | 99 | 100.0% |
