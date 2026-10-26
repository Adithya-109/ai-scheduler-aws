#!/usr/bin/env python3
"""Matrix inverse 2400x2400"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((2400, 2400)) + 2400 * np.eye(2400)
I = np.linalg.inv(A)
print('inv', float(np.trace(I)))
