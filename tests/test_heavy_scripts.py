import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import generate_heavy_scripts as g  # noqa: E402
from pipeline.feature_extractor import CodeFeatureExtractor  # noqa: E402


class HeavyScripts(unittest.TestCase):
    def test_files_on_disk_match_the_generator(self):
        for name, code in g.build().items():
            with open(os.path.join(g.OUT, name), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), code, name)

    def test_complexity_increases_with_size_within_each_scaling_family(self):
        ex = CodeFeatureExtractor()
        by_kind = {}
        for name, code in g.build().items():
            kind, n = name[:-3].rsplit("_", 1)
            f = ex.analyze(code)
            self.assertNotIn("error", f)
            by_kind.setdefault(kind, []).append((int(n), f["estimated_complexity"]))
        for kind, pts in by_kind.items():
            xs = [c for _, c in sorted(pts)]
            self.assertEqual(xs, sorted(xs), kind)
            self.assertGreater(xs[-1], xs[0], kind)


if __name__ == "__main__":
    unittest.main()
