#!/usr/bin/env python3
"""Nested loop: 2000x3000 iterations."""
result = 0
for i in range(2000):
    for j in range(3000):
        result += i ^ j
print("Nested result:", result)
