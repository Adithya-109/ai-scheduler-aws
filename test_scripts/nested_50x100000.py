#!/usr/bin/env python3
"""Nested loop: 50x100000 iterations."""
result = 0
for i in range(50):
    for j in range(100000):
        result += i ^ j
print("Nested result:", result)
