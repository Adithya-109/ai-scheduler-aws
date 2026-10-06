#!/usr/bin/env python3
"""Mixed workload: numpy + Python loop."""
import numpy as np
# Numpy part
A = np.random.rand(300, 300)
B = np.linalg.inv(A + np.eye(300))
# Python loop part
total = 0
for i in range(750000):
    total += i * 3
print("Mixed result:", B.sum(), total)
