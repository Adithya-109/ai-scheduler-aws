#!/usr/bin/env python3
"""Singular values 1000x1000"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((1000, 1000))
s = np.linalg.svd(A, compute_uv=False)
print('svd', float(s.sum()))
