#!/usr/bin/env python3
"""Triple nested loop: 200x100x30."""
result = 0
for i in range(200):
    for j in range(100):
        for k in range(30):
            result += 1
print("Triple nested:", result)
