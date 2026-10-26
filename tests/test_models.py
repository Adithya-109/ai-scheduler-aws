"""Model/artifact integrity, the routing rule, and quality gates."""
import json
import os
import sys
import unittest
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings("ignore")

import sklearn  # noqa: E402

from pipeline.feature_extractor import FEATURE_COLUMNS, FEATURE_VERSION  # noqa: E402
from pipeline.predictor import LatencyPredictor, queue_penalty  # noqa: E402
from pipeline.scheduler import OffloadingScheduler  # noqa: E402

META = json.load(open(os.path.join(ROOT, "models", "training_metadata.json")))
CODES = [open(os.path.join(ROOT, "test_scripts", f)).read()
         for f in sorted(os.listdir(os.path.join(ROOT, "test_scripts"))) if f.endswith(".py")]


class _Stub:
    """Stands in for a fitted regressor: returns log10(seconds)."""
    def __init__(self, seconds):
        self.log = __import__("math").log10(seconds)

    def predict(self, x):
        return [self.log]


def stubbed(edge_s, cloud_s, **kw):
    p = LatencyPredictor(**kw)
    p.edge_model, p.cloud_model = _Stub(edge_s), _Stub(cloud_s)
    return p


class TestArtifacts(unittest.TestCase):
    def test_metadata_matches_code(self):
        self.assertEqual(META["feature_columns"], FEATURE_COLUMNS)
        self.assertEqual(META["feature_version"], FEATURE_VERSION)

    def test_models_trained_with_installed_sklearn(self):
        self.assertEqual(META["versions"]["scikit-learn"], sklearn.__version__,
                         "models/*.pkl were trained with another scikit-learn; re-run train_model.py")
        self.assertFalse(LatencyPredictor().version_mismatch)

    def test_no_synthetic_labels_in_training(self):
        src = open(os.path.join(ROOT, "train_model.py")).read()
        self.assertNotIn("edge_scale", src)
        self.assertNotIn("modeled_edge_time", src)

    def test_dataset_is_file_keyed_and_complete(self):
        import pandas as pd
        df = pd.read_csv(os.path.join(ROOT, "hardware_benchmark.csv"))
        self.assertIn("file", df.columns)
        self.assertTrue(df.file.is_unique)
        for f in df.file:
            self.assertTrue(os.path.exists(os.path.join(ROOT, "test_scripts", f)), f)


class TestQualityGates(unittest.TestCase):
    """Out-of-fold, whole families held out (see train_model.py)."""

    def test_regressors_generalise(self):
        cv = META["cv"]
        self.assertGreater(cv["edge_r2_log_grouped"], 0.8)
        self.assertGreater(cv["cloud_r2_log_grouped"], 0.8)

    def test_scheduler_not_materially_worse_than_always_edge(self):
        self.assertLess(META["cv"]["scheduler_vs_always_edge_pct"], 10.0)

    def test_scheduler_beats_always_cloud_on_this_data(self):
        t = META["cv"]["policy_total_seconds"]
        self.assertLess(t["scheduler"], t["always_cloud"])


class TestRoutingRule(unittest.TestCase):
    F = {c: 0.0 for c in FEATURE_COLUMNS}

    def test_decision_equals_total_comparison(self):
        for rtt in (1, 20, 110, 400):
            s = OffloadingScheduler(cloud_rtt_ms=rtt)
            for c in CODES[::7]:
                r = s.schedule(c)
                p = r["predictions"]
                self.assertEqual(r["decision"] == "CLOUD", p["predicted_cloud_time"] < p["predicted_edge_time"])

    def test_heavy_job_goes_cloud_when_cloud_is_genuinely_faster(self):
        r = stubbed(10.0, 1.0, network_latency_cloud_ms=110).predict(self.F)
        self.assertEqual(r["routing_decision"], "CLOUD")
        self.assertGreater(r["confidence"], 0.9)

    def test_small_job_stays_edge_despite_faster_cloud_compute(self):
        r = stubbed(0.030, 0.005, network_latency_cloud_ms=110).predict(self.F)
        self.assertEqual(r["routing_decision"], "EDGE")

    def test_crossover_moves_with_rtt(self):
        """edge 1.0 s, cloud compute 0.4 s: cloud wins while RTT < 0.6 s."""
        wins = {ms: stubbed(1.0, 0.4, network_latency_cloud_ms=ms).predict(self.F)["routing_decision"]
                for ms in (100, 550, 650, 900)}
        self.assertEqual(wins, {100: "CLOUD", 550: "CLOUD", 650: "EDGE", 900: "EDGE"})

    def test_margin_requires_clear_win(self):
        a = stubbed(1.0, 0.5, network_latency_cloud_ms=400, margin=0.0).predict(self.F)
        b = stubbed(1.0, 0.5, network_latency_cloud_ms=400, margin=0.2).predict(self.F)
        self.assertEqual((a["routing_decision"], b["routing_decision"]), ("CLOUD", "EDGE"))

    def test_transfer_time_counts(self):
        a = stubbed(1.0, 0.5, network_latency_cloud_ms=100).predict(self.F, code_bytes=10**6)
        b = stubbed(1.0, 0.5, network_latency_cloud_ms=100, bandwidth_bytes_per_s=10**6 / 2).predict(self.F, code_bytes=10**6)
        self.assertEqual((a["routing_decision"], b["routing_decision"]), ("CLOUD", "EDGE"))
        self.assertAlmostEqual(b["transfer_s"], 2.0)

    def test_busy_cloud_pushes_work_to_edge(self):
        idle = stubbed(1.0, 0.4, network_latency_cloud_ms=100).predict(self.F)
        busy = stubbed(1.0, 0.4, network_latency_cloud_ms=100).predict(
            self.F, cloud_load={"active_jobs": 4, "cpu_count": 2})
        self.assertEqual((idle["routing_decision"], busy["routing_decision"]), ("CLOUD", "EDGE"))

    def test_queue_penalty_shape(self):
        self.assertEqual(queue_penalty(None, 1.0), 0.0)
        self.assertEqual(queue_penalty({"active_jobs": 1, "cpu_count": 2}, 1.0), 0.0)
        self.assertGreater(queue_penalty({"active_jobs": 2, "cpu_count": 2}, 1.0), 0.0)

    def test_confidence_is_probability_of_chosen_side(self):
        for edge_s, cloud_s in ((1.0, 0.2), (0.2, 1.0), (1.0, 0.99), (0.5, 0.5)):
            r = stubbed(edge_s, cloud_s, network_latency_cloud_ms=0).predict(self.F)
            self.assertGreaterEqual(r["confidence"], 0.5)
            self.assertLessEqual(r["confidence"], 1.0)

    def test_confidence_lower_when_close(self):
        far = stubbed(10.0, 1.0, network_latency_cloud_ms=0).predict(self.F)["confidence"]
        near = stubbed(1.05, 1.0, network_latency_cloud_ms=0).predict(self.F)["confidence"]
        self.assertGreater(far, near)

    def test_rtt_slider_changes_routing_below_old_training_rtt(self):
        """Regression: the old classifier vetoed any RTT below 110 ms."""
        code = open(os.path.join(ROOT, "test_scripts", "numpy_ops_10000000.py")).read()
        pred = [OffloadingScheduler(cloud_rtt_ms=r).schedule(code)["predictions"] for r in (1, 500)]
        self.assertLess(pred[0]["predicted_cloud_time"], pred[1]["predicted_cloud_time"] - 0.4)

    def test_syntax_error_reports_error(self):
        self.assertIn("error", OffloadingScheduler().schedule("def ("))

    def test_scheduling_latency_budget(self):
        import time
        s = OffloadingScheduler()
        for c in CODES[:30]:
            s.schedule(c)
        t0 = time.perf_counter()
        for c in CODES[:200]:
            s.schedule(c)
        per_call_ms = (time.perf_counter() - t0) / 200 * 1000
        self.assertLess(per_call_ms, 15.0, f"{per_call_ms:.1f} ms/call")


if __name__ == "__main__":
    unittest.main(verbosity=2)
