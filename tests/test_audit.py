"""
Audit test suite for ai-scheduler-aws.

Each test asserts the behaviour the project *should* have (per its README /
design intent). A failing test therefore marks a real defect, not a flaky test.
Run with:  python3 -m unittest -v tests.test_audit
"""
import os
import sys
import unittest
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings("ignore")

from pipeline.feature_extractor import CodeFeatureExtractor  # noqa: E402
from pipeline.predictor import LatencyPredictor  # noqa: E402
from pipeline.scheduler import OffloadingScheduler  # noqa: E402

ex = CodeFeatureExtractor()


def feats(code):
    return ex.analyze(code)


# ─────────────────────────── Feature extractor ────────────────────────────
class TestFeatureExtractor(unittest.TestCase):

    def test_basic_print(self):
        f = feats("print(1)")
        self.assertEqual(f["num_lines"], 1)
        self.assertEqual(f["num_loops"], 0)
        self.assertLess(f["estimated_complexity"], 2.0)

    def test_syntax_error_returns_error(self):
        self.assertIn("error", feats("for i in :"))

    def test_nested_depth(self):
        f = feats("for i in range(10):\n  for j in range(10):\n    pass")
        self.assertEqual(f["max_loop_depth"], 2)
        self.assertEqual(f["num_loops"], 2)

    def test_reuse_does_not_leak_state(self):
        feats("for i in range(10**6):\n  for j in range(5): pass")
        self.assertEqual(feats("print(1)")["num_loops"], 0)

    def test_empty_source(self):
        f = feats("")
        self.assertNotIn("error", f)

    # --- defects -----------------------------------------------------------
    def test_large_float_literal_does_not_crash(self):
        """float ** depth overflows before the 1e12 clamp is applied."""
        code = "for i in range(3):\n  for j in range(3):\n    x = 1e200"
        try:
            f = feats(code)
        except OverflowError as e:
            self.fail(f"OverflowError raised: {e}")
        self.assertLessEqual(f["estimated_complexity"], 12.0)

    def test_unrelated_constant_does_not_inflate_loop_cost(self):
        """A 10-iteration loop holding a big constant should not out-score a
        1,000,000-iteration loop."""
        tiny = feats("for i in range(10):\n    x = 987654321")
        big = feats("for i in range(1000000):\n    x = i")
        self.assertLess(tiny["estimated_complexity"], big["estimated_complexity"])

    def test_recursion_is_visible(self):
        """README claims recursive calls are profiled; fib(35) should look
        costlier than fib(20)."""
        src = "def fib(n):\n  return n if n<2 else fib(n-1)+fib(n-2)\nprint(fib({}))"
        self.assertGreater(feats(src.format(35))["estimated_complexity"],
                           feats(src.format(20))["estimated_complexity"])

    def test_dotted_numpy_import_detected(self):
        self.assertEqual(feats("import numpy.linalg as la\nla.inv([[1]])")["has_heavy_lib"], 1)

    def test_from_submodule_import_detected(self):
        self.assertEqual(feats("from numpy.linalg import inv")["has_heavy_lib"], 1)

    def test_set_and_dict_comprehensions_counted(self):
        f = feats("a={x for x in range(9)}\nb={x:x for x in range(9)}")
        self.assertEqual(f["num_comprehensions"], 2)

    def test_input_size_matters_for_sort(self):
        """sort_100000 vs sort_2000000 currently produce identical features."""
        a = open(os.path.join(ROOT, "test_scripts/sort_100000.py")).read()
        b = open(os.path.join(ROOT, "test_scripts/sort_2000000.py")).read()
        self.assertNotEqual(feats(a)["estimated_complexity"], feats(b)["estimated_complexity"])

    def test_numpy_complexity_not_saturated(self):
        """numpy_ops_500000 and numpy_ops_10000000 both hit the 1e12 clamp."""
        a = open(os.path.join(ROOT, "test_scripts/numpy_ops_500000.py")).read()
        b = open(os.path.join(ROOT, "test_scripts/numpy_ops_10000000.py")).read()
        self.assertLess(feats(a)["estimated_complexity"], feats(b)["estimated_complexity"])


# ─────────────────────────────── Predictor ─────────────────────────────────
SAMPLES = [open(os.path.join(ROOT, "test_scripts", f)).read()
           for f in sorted(os.listdir(os.path.join(ROOT, "test_scripts")))]


class TestPredictor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.s = OffloadingScheduler()

    def test_models_load(self):
        self.assertTrue(self.s.predictor.models_loaded)

    def test_output_schema(self):
        r = self.s.schedule("print(1)")
        for k in ("features", "predictions", "decision", "confidence", "decision_method"):
            self.assertIn(k, r)
        self.assertIn(r["decision"], ("EDGE", "CLOUD"))

    def test_huge_rtt_forces_edge(self):
        s = OffloadingScheduler(cloud_rtt_ms=100_000)
        self.assertTrue(all(s.schedule(c)["decision"] == "EDGE" for c in SAMPLES[:50]))

    def test_fallback_without_models(self):
        p = LatencyPredictor()
        p.models_loaded = False
        self.assertEqual(p.predict({"num_lines": 1})["method"], "fallback")

    # --- defects -----------------------------------------------------------
    def test_confidence_refers_to_chosen_class(self):
        """Reported confidence should be >= 0.5 for the decision actually made."""
        bad = []
        for rtt in (10, 50, 110, 300):
            s = OffloadingScheduler(cloud_rtt_ms=rtt)
            for c in SAMPLES:
                r = s.schedule(c)
                if "error" not in r and r["confidence"] < 0.5:
                    bad.append((rtt, r["decision"], r["confidence"]))
        self.assertEqual(bad, [], f"{len(bad)} decisions reported confidence < 0.5")

    def test_low_rtt_enables_offload(self):
        """The routing decision must follow the predicted totals exactly: no
        second model may veto it."""
        s = OffloadingScheduler(cloud_rtt_ms=1)
        vetoed = 0
        for c in SAMPLES:
            r = s.schedule(c)
            p = r.get("predictions", {})
            if p and p["predicted_cloud_time"] < p["predicted_edge_time"] and r["decision"] == "EDGE":
                vetoed += 1
        self.assertEqual(vetoed, 0, f"{vetoed} cloud-faster predictions kept on EDGE")

    def test_rtt_monotonic(self):
        """Raising RTT must never move a job from EDGE to CLOUD."""
        lo, hi = OffloadingScheduler(cloud_rtt_ms=20), OffloadingScheduler(cloud_rtt_ms=400)
        flips = sum(1 for c in SAMPLES
                    if lo.schedule(c).get("decision") == "EDGE"
                    and hi.schedule(c).get("decision") == "CLOUD")
        self.assertEqual(flips, 0)


# ──────────────────────────────── Worker ───────────────────────────────────
class TestWorker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from worker import runner
        cls.r = runner

    def test_executes_and_times(self):
        r = self.r.run_job("print(6*7)")
        self.assertEqual(r["stdout"].strip(), "42")
        self.assertGreater(r["execution_time_seconds"], 0)

    def test_reports_nonzero_exit(self):
        """A crashing script must be flagged so collect_data can drop it."""
        r = self.r.run_job("raise SystemExit(3)")
        self.assertEqual(r["returncode"], 3)

    def test_timeout_response_has_timing_and_flag(self):
        r = self.r.run_job("while True: pass", timeout_s=0.5)
        self.assertIn("execution_time_seconds", r)
        self.assertTrue(r["timed_out"])

    def test_requires_auth(self):
        """The HTTP front end must check an API key and refuse to listen on a
        public address without one (fastapi is optional here, so read the source)."""
        src = open(os.path.join(ROOT, "worker", "worker_server.py")).read()
        self.assertIn("verify_api_key", src)
        self.assertIn("Header(", src)
        self.assertIn("Refusing to listen", src)


# ─────────────────────────── Repo hygiene / claims ─────────────────────────
class TestRepoClaims(unittest.TestCase):

    def test_requirements_cover_imports(self):
        req = open(os.path.join(ROOT, "requirements.txt")).read().lower()
        self.assertIn("pandas", req, "pandas is imported by predictor.py but not in requirements")

    def test_versions_pinned(self):
        req = open(os.path.join(ROOT, "requirements.txt")).read()
        self.assertIn("scikit-learn==", req, "pickled models need an exact sklearn pin")

    def test_no_hardcoded_ip(self):
        hits = [f for f in ("app.py", "collect_data.py", "train_model.py")
                if "18.60.41.230" in open(os.path.join(ROOT, f)).read()]
        self.assertEqual(hits, [], f"EC2 IP hard-coded in {hits}")

    def test_readme_model_type_matches(self):
        import joblib
        clf = joblib.load(os.path.join(ROOT, "models/edge_model.pkl"))
        readme = open(os.path.join(ROOT, "README.md")).read()
        if "Random Forest" in readme:
            self.assertIn("RandomForest", type(clf).__name__,
                          f"README says Random Forest; model is {type(clf).__name__}")
        self.assertIn(type(clf).__name__, readme, "README does not name the real model class")


if __name__ == "__main__":
    unittest.main(verbosity=2)
