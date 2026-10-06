#!/usr/bin/env python3
"""Nested loop: 200x5000 iterations."""
result = 0
for i in range(200):
    for j in range(5000):
        result += i ^ j
print("Nested result:", result)
