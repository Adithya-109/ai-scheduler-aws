#!/usr/bin/env python3
"""Triple nested loop: 80x80x80."""
result = 0
for i in range(80):
    for j in range(80):
        for k in range(80):
            result += 1
print("Triple nested:", result)
