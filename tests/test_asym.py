"""The Docker two-worker dataset and the models trained on it."""
import json
import os
import sys
import unittest
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings("ignore")

from pipeline.dataset import file_sha256  # noqa: E402
from pipeline.predictor import LatencyPredictor  # noqa: E402
from pipeline.scheduler import OffloadingScheduler  # noqa: E402

DATA = os.path.join(ROOT, "data", "docker_asym_v1", "asym_benchmark.csv")
ASYM = os.path.join(ROOT, "models", "asym")


class AsymTests(unittest.TestCase):
    def test_metadata_matches_the_data_and_records_hardware(self):
        meta = json.load(open(os.path.join(ASYM, "training_metadata.json")))
        self.assertEqual(meta["data_sha256"], file_sha256(DATA))
        self.assertIn("cpus=0.5", meta["hardware"]["edge"])
        self.assertIn("cpus=4", meta["hardware"]["cloud"])
        self.assertEqual(meta["training_samples"], 591)
        self.assertIsNone(meta.get("synthetic"))

    def test_asym_models_load_and_route_by_env(self):
        pred = LatencyPredictor(models_dir=ASYM)
        self.assertTrue(pred.models_loaded)
        os.environ["SCHEDULER_MODELS_DIR"] = ASYM
        try:
            sched = OffloadingScheduler(cloud_rtt_ms=110)
            self.assertTrue(sched.predictor.models_loaded)
            heavy = "import numpy as np\na=np.random.rand(2500,2500)\nprint((a@a).sum())\n"
            tiny = "print(1)\n"
            self.assertEqual(sched.schedule(tiny)["decision"], "EDGE")
            self.assertIn(sched.schedule(heavy)["decision"], ("EDGE", "CLOUD"))
        finally:
            del os.environ["SCHEDULER_MODELS_DIR"]

    def test_cv_result_beats_always_edge(self):
        cv = json.load(open(os.path.join(ASYM, "training_metadata.json")))["cv"]
        self.assertLess(cv["scheduler_vs_always_edge_pct"], 0)
        self.assertLess(cv["policy_total_seconds"]["scheduler"], cv["policy_total_seconds"]["always_cloud"])

    def test_report_reproduces_training_numbers_with_interval(self):
        import re
        import subprocess
        out = subprocess.run([sys.executable, "-W", "ignore", os.path.join(ROOT, "bench", "asym_report.py"), DATA,
                              "--rtt-ms", "110", "--bootstrap", "200"], capture_output=True, text=True, check=True).stdout
        rel = float(re.search(r"always-edge: ([+-][\d.]+)%", out).group(1))
        cv = json.load(open(os.path.join(ASYM, "training_metadata.json")))["cv"]
        self.assertAlmostEqual(rel, cv["scheduler_vs_always_edge_pct"], delta=0.06)
        lo, hi = map(float, re.search(r"scripts \[([+-][\d.]+)%, ([+-][\d.]+)%\]", out).groups())
        self.assertLess(lo, rel)
        self.assertGreater(hi, rel)
        self.assertLess(hi, 0)  # the whole interval is below zero


if __name__ == "__main__":
    unittest.main()
