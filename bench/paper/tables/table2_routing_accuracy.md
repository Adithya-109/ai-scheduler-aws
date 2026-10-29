| Dataset | Subset | n | Accuracy (95% CI) | Majority baseline | Balanced acc. | Precision | Recall | F1 | MCC | TP/FP/FN/TN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Similar hardware | AI Scheduler, all | 495 | 99.8% (98.9–100.0) | 99.8% | 50.0% | 0.0% | 0.0% | 0.000 | 0.000 | 0/0/1/494 |
| Similar hardware | AI Scheduler, decisive | 465 | 100.0% (99.2–100.0) | 100.0% | n/a | 0.0% | 0.0% | 0.000 | n/a | 0/0/0/465 |
| Similar hardware | Static threshold, all | 495 | 99.8% (98.9–100.0) | 99.8% | 50.0% | 0.0% | 0.0% | 0.000 | 0.000 | 0/0/1/494 |
| Asymmetric (591) | AI Scheduler, all | 591 | 95.8% (93.8–97.1) | 89.7% | 88.2% | 80.0% | 78.7% | 0.793 | 0.770 | 48/12/13/518 |
| Asymmetric (591) | AI Scheduler, decisive | 521 | 97.9% (96.3–98.8) | 90.2% | 94.5% | 88.5% | 90.2% | 0.893 | 0.882 | 46/6/5/464 |
| Asymmetric (591) | Static threshold, all | 591 | 87.1% (84.2–89.6) | 89.7% | 84.1% | 43.4% | 80.3% | 0.563 | 0.528 | 49/64/12/466 |
| Asymmetric + heavy (633) | AI Scheduler, all | 633 | 96.5% (94.8–97.7) | 84.4% | 93.0% | 89.7% | 87.9% | 0.888 | 0.867 | 87/10/12/524 |
| Asymmetric + heavy (633) | AI Scheduler, decisive | 559 | 98.4% (97.0–99.2) | 84.1% | 97.2% | 94.4% | 95.5% | 0.950 | 0.940 | 85/5/4/465 |
| Asymmetric + heavy (633) | Static threshold, all | 633 | 87.2% (84.4–89.6) | 84.4% | 88.7% | 55.6% | 90.9% | 0.690 | 0.644 | 90/72/9/462 |
| Real EC2 c7i-flex.large | AI Scheduler, all | 633 | 95.6% (93.7–96.9) | 87.0% | 92.3% | 80.0% | 87.8% | 0.837 | 0.813 | 72/18/10/533 |
| Real EC2 c7i-flex.large | AI Scheduler, decisive | 595 | 96.6% (94.9–97.8) | 87.1% | 93.6% | 85.2% | 89.6% | 0.873 | 0.854 | 69/12/8/506 |
| Real EC2 c7i-flex.large | Static threshold, all | 633 | 85.3% (82.3–87.9) | 87.0% | 86.4% | 46.5% | 87.8% | 0.608 | 0.568 | 72/83/10/468 |
