#!/usr/bin/env python3
"""Triple nested loop: 50x50x200."""
result = 0
for i in range(50):
    for j in range(50):
        for k in range(200):
            result += 1
print("Triple nested:", result)
