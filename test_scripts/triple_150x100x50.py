#!/usr/bin/env python3
"""Triple nested loop: 150x100x50."""
result = 0
for i in range(150):
    for j in range(100):
        for k in range(50):
            result += 1
print("Triple nested:", result)
