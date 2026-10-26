#!/usr/bin/env python3
"""Linear solve 4000x4000"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((4000, 4000)) + 4000 * np.eye(4000)
b = rng.random(4000)
x = np.linalg.solve(A, b)
print('solve', float(x.sum()))
