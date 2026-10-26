#!/usr/bin/env python3
"""Dense matmul 4000x4000"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((4000, 4000))
B = rng.random((4000, 4000))
C = A @ B
print('matmul', float(C.sum()))
