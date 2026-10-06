#!/usr/bin/env python3
"""Triple nested loop: 200x200x20."""
result = 0
for i in range(200):
    for j in range(200):
        for k in range(20):
            result += 1
print("Triple nested:", result)
