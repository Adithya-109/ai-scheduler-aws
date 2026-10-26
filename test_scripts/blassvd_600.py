#!/usr/bin/env python3
"""Singular values 600x600"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((600, 600))
s = np.linalg.svd(A, compute_uv=False)
print('svd', float(s.sum()))
