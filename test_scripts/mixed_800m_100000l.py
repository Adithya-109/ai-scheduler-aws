#!/usr/bin/env python3
"""Mixed workload: numpy + Python loop."""
import numpy as np
# Numpy part
A = np.random.rand(800, 800)
B = np.linalg.inv(A + np.eye(800))
# Python loop part
total = 0
for i in range(100000):
    total += i * 3
print("Mixed result:", B.sum(), total)
