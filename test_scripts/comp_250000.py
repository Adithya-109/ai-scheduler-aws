#!/usr/bin/env python3
"""List comprehension: 250000 elements with filtering."""
data = [x**2 + x for x in range(250000)]
evens = [x for x in data if x % 2 == 0]
odds = [x for x in data if x % 2 == 1]
result = sum(evens) - sum(odds)
print("Comprehension result:", result, "evens:", len(evens))
