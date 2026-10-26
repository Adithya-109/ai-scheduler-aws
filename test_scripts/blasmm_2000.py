#!/usr/bin/env python3
"""Dense matmul 2000x2000"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((2000, 2000))
B = rng.random((2000, 2000))
C = A @ B
print('matmul', float(C.sum()))
