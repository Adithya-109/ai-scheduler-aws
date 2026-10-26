#!/usr/bin/env python3
"""Linear solve 3000x3000"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((3000, 3000)) + 3000 * np.eye(3000)
b = rng.random(3000)
x = np.linalg.solve(A, b)
print('solve', float(x.sum()))
