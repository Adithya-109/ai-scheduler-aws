#!/usr/bin/env python3
"""Singular values 400x400"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((400, 400))
s = np.linalg.svd(A, compute_uv=False)
print('svd', float(s.sum()))
