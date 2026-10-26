#!/usr/bin/env python3
"""Linear solve 3500x3500"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((3500, 3500)) + 3500 * np.eye(3500)
b = rng.random(3500)
x = np.linalg.solve(A, b)
print('solve', float(x.sum()))
