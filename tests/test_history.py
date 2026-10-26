import os
import sys
import tempfile
import unittest
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings("ignore")

from pipeline.history import RuntimeHistory  # noqa: E402
from pipeline.scheduler import OffloadingScheduler  # noqa: E402
from pipeline.telemetry import DecisionLog  # noqa: E402

CODE = "x = 0\nfor i in range(10):\n    x += i\nprint(x)\n"


class HistoryTests(unittest.TestCase):
    def test_needs_min_observations_and_uses_median(self):
        h = RuntimeHistory(min_obs=2)
        h.observe("a", "edge", 1.0)
        self.assertIsNone(h.median("a", "edge"))
        h.observe("a", "edge", 3.0)
        h.observe("a", "edge", 2.0)
        self.assertEqual(h.median("a", "edge"), 2.0)
        self.assertIsNone(h.median("a", "cloud"))

    def test_failures_and_bad_values_ignored(self):
        h = RuntimeHistory(min_obs=1)
        h.observe("a", "edge", 5.0, ok=False)
        h.observe("a", "edge", None)
        h.observe("a", "edge", -1.0)
        h.observe("a", "gpu", 1.0)
        self.assertIsNone(h.median("a", "edge"))

    def test_from_log_skips_timeouts(self):
        with tempfile.TemporaryDirectory() as d:
            log = DecisionLog(os.path.join(d, "l.jsonl"))
            log.record(code_hash="h", target="edge", compute_time_s=2.0, returncode=0, timed_out=False)
            log.record(code_hash="h", target="edge", compute_time_s=30.0, returncode=-9, timed_out=True)
            log.record(code_hash="h", target="edge", compute_time_s=4.0, returncode=0, timed_out=False)
            h = RuntimeHistory.from_log(log)
            self.assertEqual(h.median("h", "edge"), 3.0)

    def test_scheduler_overrides_regression_and_routes_on_observations(self):
        base = OffloadingScheduler(cloud_rtt_ms=100)
        plan0 = base.schedule(CODE)
        self.assertEqual(plan0["decision_method"], "regression")
        h = RuntimeHistory(min_obs=1)
        h.observe(plan0["code_hash"], "edge", 20.0)
        h.observe(plan0["code_hash"], "cloud", 2.0)
        sched = OffloadingScheduler(cloud_rtt_ms=100, history=h)
        plan = sched.schedule(CODE)
        self.assertEqual(plan["decision_method"], "history")
        self.assertEqual(plan["decision"], "CLOUD")
        self.assertAlmostEqual(plan["predictions"]["predicted_edge_compute"], 20.0, places=2)
        self.assertGreater(plan["confidence"], 0.99)

    def test_partial_history_marks_method(self):
        base = OffloadingScheduler(cloud_rtt_ms=100)
        hsh = base.schedule(CODE)["code_hash"]
        h = RuntimeHistory(min_obs=1)
        h.observe(hsh, "edge", 0.5)
        plan = OffloadingScheduler(cloud_rtt_ms=100, history=h).schedule(CODE)
        self.assertEqual(plan["decision_method"], "regression+history")
        self.assertEqual(plan["predictions"]["observed_sides"], ["edge"])


if __name__ == "__main__":
    unittest.main()
