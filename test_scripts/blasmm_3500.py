#!/usr/bin/env python3
"""Dense matmul 3500x3500"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((3500, 3500))
B = rng.random((3500, 3500))
C = A @ B
print('matmul', float(C.sum()))
