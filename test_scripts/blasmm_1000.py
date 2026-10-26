#!/usr/bin/env python3
"""Dense matmul 1000x1000"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((1000, 1000))
B = rng.random((1000, 1000))
C = A @ B
print('matmul', float(C.sum()))
