#!/usr/bin/env python3
"""Linear solve 2000x2000"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((2000, 2000)) + 2000 * np.eye(2000)
b = rng.random(2000)
x = np.linalg.solve(A, b)
print('solve', float(x.sum()))
