#!/usr/bin/env python3
"""Dense matmul 1500x1500"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((1500, 1500))
B = rng.random((1500, 1500))
C = A @ B
print('matmul', float(C.sum()))
