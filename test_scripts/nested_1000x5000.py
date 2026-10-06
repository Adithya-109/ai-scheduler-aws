#!/usr/bin/env python3
"""Nested loop: 1000x5000 iterations."""
result = 0
for i in range(1000):
    for j in range(5000):
        result += i ^ j
print("Nested result:", result)
