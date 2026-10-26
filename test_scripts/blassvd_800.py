#!/usr/bin/env python3
"""Singular values 800x800"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((800, 800))
s = np.linalg.svd(A, compute_uv=False)
print('svd', float(s.sum()))
