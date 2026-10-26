"""Unseen-workload holdout: stored timings vs the CURRENT extractor (deterministic)."""
import json
import os
import unittest

from bench.holdout import HOLD, ROOT, spearman
from pipeline.feature_extractor import CodeFeatureExtractor


class HoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "bench", "holdout_results.json")) as fh:
            cls.stored = json.load(fh)

    def test_scripts_match_stored_results(self):
        files = sorted(f for f in os.listdir(HOLD) if f.endswith(".py"))
        self.assertEqual(files, [r["file"] for r in self.stored["rows"]])

    def test_rank_correlation_floor(self):
        ex = CodeFeatureExtractor()
        cx, t = [], []
        for r in self.stored["rows"]:
            code = open(os.path.join(HOLD, r["file"]), encoding="utf-8").read()
            f = ex.analyze(code)
            self.assertFalse(f.get("analysis_degraded"), r["file"])
            cx.append(f["estimated_complexity"])
            t.append(r["seconds"])
        # 0.43 when first measured, 0.39 after re-timing and the Generator-size fix (n=16, so within noise);
        # the floor catches regressions, not noise.
        self.assertGreater(spearman(cx, t), 0.30)


if __name__ == "__main__":
    unittest.main()
