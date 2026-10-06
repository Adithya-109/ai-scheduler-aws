#!/usr/bin/env python3
"""Heavy pure-Python loop: 1000000 iterations."""
result = 0
for i in range(1000000):
    result += i * 3 + 7
print("Loop result:", result)
