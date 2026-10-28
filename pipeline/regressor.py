"""Latency regressor: a robust linear model on the static work counters, plus
gradient-boosted trees on what the linear part leaves over.

Trees alone cannot extrapolate: a script family whose work counters lie beyond
anything seen in training (e.g. the first BLAS-heavy family) gets the largest
leaf value it has, so a 4 s matmul was predicted at 0.07 s and never offloaded.
The linear part grows with the log work estimate and carries the prediction
into unseen ranges; the trees correct it where the data does exist.
"""
from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import HuberRegressor

from pipeline.feature_extractor import FEATURE_COLUMNS

WORK_COLUMNS = ("estimated_complexity", "log_python_ops", "log_numpy_elems", "log_blas_flops")


def make_tree_regressor(learning_rate: float = 0.06, max_iter: int = 300) -> HistGradientBoostingRegressor:
    """Defaults are the v2.0 stand-alone model; the residual stage uses fewer, larger steps
    (same accuracy, about half the trees, so a single-row prediction is ~2x faster)."""
    return HistGradientBoostingRegressor(
        max_iter=max_iter, learning_rate=learning_rate, max_depth=5, min_samples_leaf=5,
        l2_regularization=0.1, early_stopping=True, validation_fraction=0.15,
        n_iter_no_change=20, random_state=42,
    )


class LinearPlusTreesRegressor(BaseEstimator, RegressorMixin):
    """y = Huber(work columns) + HistGradientBoosting(all features) on the residual."""

    def __init__(self, base_columns=WORK_COLUMNS, feature_columns=tuple(FEATURE_COLUMNS)):
        self.base_columns = base_columns
        self.feature_columns = feature_columns

    def _base(self, X):
        idx = [list(self.feature_columns).index(c) for c in self.base_columns]
        return np.asarray(X, dtype=float)[:, idx]

    def fit(self, X, y):
        X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=float)
        self.linear_ = HuberRegressor(max_iter=1000).fit(self._base(X), y)
        self.trees_ = make_tree_regressor(learning_rate=0.1, max_iter=100).fit(X, y - self.linear_.predict(self._base(X)))
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        return self.linear_.predict(self._base(X)) + self.trees_.predict(X)
