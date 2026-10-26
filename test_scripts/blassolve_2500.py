#!/usr/bin/env python3
"""Linear solve 2500x2500"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((2500, 2500)) + 2500 * np.eye(2500)
b = rng.random(2500)
x = np.linalg.solve(A, b)
print('solve', float(x.sum()))
