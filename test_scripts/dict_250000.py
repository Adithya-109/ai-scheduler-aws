#!/usr/bin/env python3
"""Dictionary insert + lookup: 250000 operations."""
data = {}
for i in range(250000):
    data[f"key_{i}_{i**2}"] = i * 7 + 3
lookups = 0
for i in range(250000):
    if f"key_{i}_{i**2}" in data:
        lookups += 1
print("Dict size:", len(data), "lookups:", lookups)
