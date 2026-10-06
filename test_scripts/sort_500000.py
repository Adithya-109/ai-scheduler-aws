#!/usr/bin/env python3
"""Sort a list of 500000 random integers."""
import random
random.seed(42)
data = [random.randint(0, 10**9) for _ in range(500000)]
data.sort()
print("Sorted", len(data), "elements, first:", data[0], "last:", data[-1])
