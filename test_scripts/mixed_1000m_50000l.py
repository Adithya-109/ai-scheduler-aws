#!/usr/bin/env python3
"""Mixed workload: numpy + Python loop."""
import numpy as np
# Numpy part
A = np.random.rand(1000, 1000)
B = np.linalg.inv(A + np.eye(1000))
# Python loop part
total = 0
for i in range(50000):
    total += i * 3
print("Mixed result:", B.sum(), total)
