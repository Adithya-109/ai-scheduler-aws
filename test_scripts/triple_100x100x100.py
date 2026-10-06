#!/usr/bin/env python3
"""Triple nested loop: 100x100x100."""
result = 0
for i in range(100):
    for j in range(100):
        for k in range(100):
            result += 1
print("Triple nested:", result)
