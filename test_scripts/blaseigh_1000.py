#!/usr/bin/env python3
"""Symmetric eigendecomposition 1000x1000"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((1000, 1000))
S = A + A.T
w = np.linalg.eigvalsh(S)
print('eigh', float(w.sum()))
