#!/usr/bin/env python3
"""Numpy matrix multiplication: 200x200."""
import numpy as np
size = 200
A = np.random.rand(size, size)
B = np.random.rand(size, size)
C = np.dot(A, B)
print("Matrix shape:", C.shape, "sum:", C.sum())
