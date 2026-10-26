#!/usr/bin/env python3
"""Matrix inverse 1600x1600"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((1600, 1600)) + 1600 * np.eye(1600)
I = np.linalg.inv(A)
print('inv', float(np.trace(I)))
