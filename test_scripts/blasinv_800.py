#!/usr/bin/env python3
"""Matrix inverse 800x800"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((800, 800)) + 800 * np.eye(800)
I = np.linalg.inv(A)
print('inv', float(np.trace(I)))
