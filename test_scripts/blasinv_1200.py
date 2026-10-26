#!/usr/bin/env python3
"""Matrix inverse 1200x1200"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((1200, 1200)) + 1200 * np.eye(1200)
I = np.linalg.inv(A)
print('inv', float(np.trace(I)))
