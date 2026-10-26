#!/usr/bin/env python3
"""Dense matmul 3000x3000"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((3000, 3000))
B = rng.random((3000, 3000))
C = A @ B
print('matmul', float(C.sum()))
