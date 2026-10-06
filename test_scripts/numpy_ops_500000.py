#!/usr/bin/env python3
"""Numpy array operations on 500000 elements."""
import numpy as np
arr = np.random.rand(500000)
result = np.sort(arr)
result = np.fft.fft(result[:min(len(result), 100000)])
print("Array ops done, shape:", result.shape)
