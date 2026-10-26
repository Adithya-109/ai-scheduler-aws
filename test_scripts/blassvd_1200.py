#!/usr/bin/env python3
"""Singular values 1200x1200"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((1200, 1200))
s = np.linalg.svd(A, compute_uv=False)
print('svd', float(s.sum()))
