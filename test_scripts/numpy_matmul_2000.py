#!/usr/bin/env python3
"""Numpy matrix multiplication: 2000x2000."""
import numpy as np
size = 2000
A = np.random.rand(size, size)
B = np.random.rand(size, size)
C = np.dot(A, B)
print("Matrix shape:", C.shape, "sum:", C.sum())
