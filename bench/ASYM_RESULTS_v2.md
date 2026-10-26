# Asymmetric two-worker experiment

633 scripts, 29 families, simulated RTT 110 ms, 5-fold grouped out-of-fold predictions.

| Policy | Total (s) | vs always-edge |
| --- | ---: | ---: |
| oracle | 262.8 | -24.4% |
| always edge | 347.5 | +0.0% |
| scheduler | 264.5 | -23.9% |
| always cloud | 316.0 | -9.1% |

* Cloud faster than edge incl. RTT on 99/633 scripts; scheduler routed 93 to cloud.
* Time saved on 84 scripts: 83.5s; lost on 9: 0.5s.
* R2 (log10, families held out): edge 0.965, cloud 0.973.
* 95% bootstrap CI vs always-edge: scripts [-31.4%, -17.2%], families [-45.0%, -10.3%].

Both workers ran on one machine (CPU limits differ); the network delay is simulated. This is not an EC2 measurement.
