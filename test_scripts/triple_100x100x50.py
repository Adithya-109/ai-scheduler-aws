#!/usr/bin/env python3
"""Triple nested loop: 100x100x50."""
result = 0
for i in range(100):
    for j in range(100):
        for k in range(50):
            result += 1
print("Triple nested:", result)
