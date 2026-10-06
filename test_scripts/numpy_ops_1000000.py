#!/usr/bin/env python3
"""Numpy array operations on 1000000 elements."""
import numpy as np
arr = np.random.rand(1000000)
result = np.sort(arr)
result = np.fft.fft(result[:min(len(result), 100000)])
print("Array ops done, shape:", result.shape)
