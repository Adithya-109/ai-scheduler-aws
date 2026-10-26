#!/usr/bin/env python3
"""Symmetric eigendecomposition 600x600"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((600, 600))
S = A + A.T
w = np.linalg.eigvalsh(S)
print('eigh', float(w.sum()))
