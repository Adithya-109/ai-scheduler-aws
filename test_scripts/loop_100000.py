#!/usr/bin/env python3
"""Heavy pure-Python loop: 100000 iterations."""
result = 0
for i in range(100000):
    result += i * 3 + 7
print("Loop result:", result)
