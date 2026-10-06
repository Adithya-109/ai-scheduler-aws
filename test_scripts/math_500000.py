#!/usr/bin/env python3
"""Pure math operations: 500000 iterations of trig-like computation."""
result = 1.0
for i in range(1, 500000):
    result = (result * i) % 1000000007
    result += (i * i) % 997
print("Math result:", result)
