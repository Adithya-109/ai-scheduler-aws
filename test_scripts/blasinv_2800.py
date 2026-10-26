#!/usr/bin/env python3
"""Matrix inverse 2800x2800"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((2800, 2800)) + 2800 * np.eye(2800)
I = np.linalg.inv(A)
print('inv', float(np.trace(I)))
