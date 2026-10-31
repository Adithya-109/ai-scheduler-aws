| Workload | Pred. edge (s) | Pred. cloud incl. RTT (s) | Routed to | Measured edge (s) | Measured cloud end-to-end (s) | Faster node | Correct |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | :---: |
| `numpy_matmul_2000.py` | 1.268 | 0.474 | Cloud | 1.448 | 0.651 | Cloud | yes |
| `blassvd_1000.py` | 0.598 | 0.363 | Cloud | 1.188 | 0.695 | Cloud | yes |
| `nested_2000x3000.py` | 1.705 | 0.634 | Cloud | 1.234 | 0.754 | Cloud | yes |
| `fib_35.py` | 12.282 | 4.151 | Cloud | 2.119 | 1.047 | Cloud | yes |
| `sort_1000000.py` | 0.541 | 0.379 | Cloud | 1.520 | 0.758 | Cloud | yes |
| `dict_1000000.py` | 0.587 | 0.486 | Cloud | 3.563 | 1.280 | Cloud | yes |
| `fib_33.py` | 8.830 | 3.075 | Cloud | 0.804 | 0.909 | Edge | no |
| `string_250000.py` | 0.103 | 0.253 | Edge | 0.171 | 0.211 | Edge | yes |
| `fib_24.py` | 0.130 | 0.194 | Edge | 0.028 | 0.205 | Edge | yes |
| `string_50000.py` | 0.045 | 0.205 | Edge | 0.032 | 0.174 | Edge | yes |
| `script_001.py` | 0.019 | 0.169 | Edge | 0.015 | 0.163 | Edge | yes |
