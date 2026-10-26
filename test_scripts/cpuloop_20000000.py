#!/usr/bin/env python3
"""Single-threaded pure-Python loop, 20000000 iterations (control)"""
total = 0
for i in range(20000000):
    total += (i * i) % 7
print('loop', total)
