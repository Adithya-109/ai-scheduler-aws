#!/usr/bin/env python3
"""Dense matmul 2500x2500"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((2500, 2500))
B = rng.random((2500, 2500))
C = A @ B
print('matmul', float(C.sum()))
