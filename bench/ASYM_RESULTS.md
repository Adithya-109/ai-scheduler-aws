# Asymmetric two-worker experiment

591 scripts, 21 families, simulated RTT 110 ms, 5-fold grouped out-of-fold predictions.

| Policy | Total (s) | vs always-edge |
| --- | ---: | ---: |
| oracle | 237.8 | -13.1% |
| always edge | 273.7 | +0.0% |
| scheduler | 239.7 | -12.4% |
| always cloud | 291.1 | +6.4% |

* Cloud faster than edge incl. RTT on 61/591 scripts; scheduler routed 60 to cloud.
* Time saved on 48 scripts: 34.8s; lost on 12: 0.9s.
* R2 (log10, families held out): edge 0.794, cloud 0.891.
* 95% bootstrap CI vs always-edge: scripts [-18.5%, -7.8%], families [-29.9%, -3.9%].

Both workers ran on one machine (CPU limits differ); the network delay is simulated. This is not an EC2 measurement.
