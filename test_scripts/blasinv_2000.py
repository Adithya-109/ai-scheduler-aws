#!/usr/bin/env python3
"""Matrix inverse 2000x2000"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((2000, 2000)) + 2000 * np.eye(2000)
I = np.linalg.inv(A)
print('inv', float(np.trace(I)))
