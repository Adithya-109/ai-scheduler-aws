# Asymmetric two-worker experiment

591 scripts, 21 families, simulated RTT 110 ms, 5-fold grouped out-of-fold predictions.

| Policy | Total (s) | vs always-edge |
| --- | ---: | ---: |
| oracle | 237.8 | -13.1% |
| always edge | 273.7 | +0.0% |
| scheduler | 254.8 | -6.9% |
| always cloud | 291.1 | +6.4% |

* Cloud faster than edge incl. RTT on 61/591 scripts; scheduler routed 43 to cloud.
* Time saved on 32 scripts: 19.7s; lost on 11: 0.9s.
* R2 (log10, families held out): edge 0.924, cloud 0.941.
* 95% bootstrap CI vs always-edge: scripts [-10.8%, -3.8%], families [-18.5%, -1.8%].

Both workers ran on one machine (CPU limits differ); the network delay is simulated. This is not an EC2 measurement.
