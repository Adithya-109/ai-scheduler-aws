#!/usr/bin/env python3
"""Numpy matrix multiplication: 2500x2500."""
import numpy as np
size = 2500
A = np.random.rand(size, size)
B = np.random.rand(size, size)
C = np.dot(A, B)
print("Matrix shape:", C.shape, "sum:", C.sum())
