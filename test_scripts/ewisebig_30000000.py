#!/usr/bin/env python3
"""Element-wise chain over 30000000 floats"""
import numpy as np
rng = np.random.default_rng(0)
x = rng.random(30000000)
y = np.sqrt(x * x + 1.0) * np.exp(-x) + np.sin(x)
print('ewise', float(y.sum()))
