import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.feature_extractor import FEATURE_COLUMNS  # noqa: E402
from pipeline.regressor import LinearPlusTreesRegressor, make_tree_regressor  # noqa: E402


class TestExtrapolation(unittest.TestCase):
    """The reason for the linear term: a job with more work than anything in training."""

    def setUp(self):
        rng = np.random.default_rng(0)
        cx = rng.uniform(0, 5, 400)
        self.X = np.zeros((400, len(FEATURE_COLUMNS)))
        self.X[:, FEATURE_COLUMNS.index("estimated_complexity")] = cx
        self.y = cx - 7 + rng.normal(0, 0.05, 400)  # log10 seconds grows with log work
        self.unseen = np.zeros((1, len(FEATURE_COLUMNS)))
        self.unseen[0, FEATURE_COLUMNS.index("estimated_complexity")] = 8.0  # 1000x beyond the training range

    def test_hybrid_extrapolates_where_trees_saturate(self):
        hybrid = LinearPlusTreesRegressor().fit(self.X, self.y).predict(self.unseen)[0]
        trees = make_tree_regressor().fit(self.X, self.y).predict(self.unseen)[0]
        self.assertAlmostEqual(hybrid, 1.0, delta=0.3)
        self.assertLess(trees, -1.5)  # stuck near the largest training target (-2)

    def test_matches_trees_inside_the_training_range(self):
        inside = self.X[:50]
        hybrid = LinearPlusTreesRegressor().fit(self.X, self.y).predict(inside)
        self.assertLess(np.abs(hybrid - self.y[:50]).max(), 0.3)


if __name__ == "__main__":
    unittest.main()
