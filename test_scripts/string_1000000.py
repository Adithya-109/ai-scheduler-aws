#!/usr/bin/env python3
"""Heavy string concatenation and processing: 1000000 iterations."""
parts = []
for i in range(1000000):
    parts.append(str(i) * 3)
big_string = ",".join(parts)
count = big_string.count("1")
print("String length:", len(big_string), "count of 1:", count)
