#!/usr/bin/env python3
"""FFT of 2**23 points, repeated"""
import numpy as np
rng = np.random.default_rng(0)
x = rng.random(2 ** 23)
t = 0.0
for _ in range(4):
    t += float(np.abs(np.fft.rfft(x)).sum())
print('fft', t)
