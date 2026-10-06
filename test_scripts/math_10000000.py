#!/usr/bin/env python3
"""Pure math operations: 10000000 iterations of trig-like computation."""
result = 1.0
for i in range(1, 10000000):
    result = (result * i) % 1000000007
    result += (i * i) % 997
print("Math result:", result)
