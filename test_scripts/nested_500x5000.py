#!/usr/bin/env python3
"""Nested loop: 500x5000 iterations."""
result = 0
for i in range(500):
    for j in range(5000):
        result += i ^ j
print("Nested result:", result)
