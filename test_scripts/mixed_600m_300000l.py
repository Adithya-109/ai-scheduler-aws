#!/usr/bin/env python3
"""Mixed workload: numpy + Python loop."""
import numpy as np
# Numpy part
A = np.random.rand(600, 600)
B = np.linalg.inv(A + np.eye(600))
# Python loop part
total = 0
for i in range(300000):
    total += i * 3
print("Mixed result:", B.sum(), total)
