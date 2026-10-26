#!/usr/bin/env python3
"""Linear solve 1500x1500"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((1500, 1500)) + 1500 * np.eye(1500)
b = rng.random(1500)
x = np.linalg.solve(A, b)
print('solve', float(x.sum()))
