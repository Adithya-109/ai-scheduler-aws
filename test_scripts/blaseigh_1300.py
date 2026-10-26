#!/usr/bin/env python3
"""Symmetric eigendecomposition 1300x1300"""
import numpy as np
rng = np.random.default_rng(0)
A = rng.random((1300, 1300))
S = A + A.T
w = np.linalg.eigvalsh(S)
print('eigh', float(w.sum()))
