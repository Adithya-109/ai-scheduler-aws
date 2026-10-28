# Asymmetric two-worker experiment

633 scripts, 29 families, simulated RTT 110 ms, 5-fold grouped out-of-fold predictions.

| Policy | Total (s) | vs always-edge |
| --- | ---: | ---: |
| oracle | 262.8 | -24.4% |
| always edge | 347.5 | +0.0% |
| scheduler | 263.7 | -24.1% |
| always cloud | 316.0 | -9.1% |

* Cloud faster than edge incl. RTT on 99/633 scripts; scheduler routed 97 to cloud.
* Time saved on 87 scripts: 84.3s; lost on 10: 0.5s.
* R2 (log10, families held out): edge 0.953, cloud 0.959.
* 95% bootstrap CI vs always-edge: scripts [-31.6%, -17.5%], families [-45.1%, -10.6%].

Both workers ran on one machine (CPU limits differ); the network delay is simulated. This is not an EC2 measurement.
