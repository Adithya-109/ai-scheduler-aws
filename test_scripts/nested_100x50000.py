#!/usr/bin/env python3
"""Nested loop: 100x50000 iterations."""
result = 0
for i in range(100):
    for j in range(50000):
        result += i ^ j
print("Nested result:", result)
