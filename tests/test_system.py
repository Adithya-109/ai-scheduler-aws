"""Integration tests over real sockets: auth, limits, dispatcher fallback,
circuit breaker, decision log, live RTT, and collect_data."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings("ignore")

import requests  # noqa: E402

from pipeline.dispatcher import CircuitBreaker, Dispatcher, WorkerClient, WorkerError  # noqa: E402
from pipeline.rtt import RttTracker  # noqa: E402
from pipeline.scheduler import OffloadingScheduler  # noqa: E402
from pipeline.telemetry import DecisionLog  # noqa: E402
from tests.mock_worker import MockWorker  # noqa: E402
from worker.runner import JobSlots, Limits, run_job, verify_api_key  # noqa: E402

HEAVY = "x = 0\nfor i in range(30000000):\n    x += i\n"  # predicted heavy


class TestRunner(unittest.TestCase):
    def test_result_always_has_timing_and_status(self):
        for code in ("print(1)", "raise SystemExit(3)"):
            r = run_job(code)
            for k in ("execution_time_seconds", "returncode", "timed_out"):
                self.assertIn(k, r)

    def test_exit_status_reported(self):
        self.assertEqual(run_job("raise SystemExit(3)")["returncode"], 3)

    def test_timeout_kills_and_reports(self):
        r = run_job("while True: pass", timeout_s=0.4)
        self.assertTrue(r["timed_out"])
        self.assertGreater(r["execution_time_seconds"], 0.3)
        self.assertLess(r["execution_time_seconds"], 3)

    def test_timeout_kills_child_processes(self):
        code = ("import subprocess,sys,time\n"
                "subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\n"
                "time.sleep(60)\n")
        t0 = time.time()
        r = run_job(code, timeout_s=0.5)
        self.assertTrue(r["timed_out"])
        self.assertLess(time.time() - t0, 5)

    def test_secrets_not_inherited(self):
        os.environ["WORKER_API_KEY"] = "super-secret"
        try:
            r = run_job("import os; print([k for k in os.environ if 'KEY' in k or 'SECRET' in k])")
        finally:
            del os.environ["WORKER_API_KEY"]
        self.assertEqual(r["stdout"].strip(), "[]")

    def test_memory_limit(self):
        r = run_job("x = bytearray(3 * 1024**3)", Limits(mem_mb=256))
        self.assertNotEqual(r["returncode"], 0)
        self.assertIn("MemoryError", r["stderr"])

    def test_output_truncated(self):
        r = run_job("print('a' * 500000)", Limits(max_output_bytes=1000))
        self.assertTrue(r["truncated"])
        self.assertLess(len(r["stdout"]), 1100)

    def test_oversized_code_rejected(self):
        r = run_job("#" + "x" * 500, Limits(max_code_bytes=100))
        self.assertTrue(r.get("rejected"))

    def test_runs_in_private_cwd(self):
        r = run_job("import os; open('f.txt','w').write('x'); print(os.getcwd())")
        self.assertFalse(os.path.exists(os.path.join(r["stdout"].strip(), "f.txt")))

    def test_api_key_check(self):
        self.assertTrue(verify_api_key("k", "k"))
        self.assertFalse(verify_api_key("x", "k"))
        self.assertFalse(verify_api_key(None, "k"))
        self.assertTrue(verify_api_key(None, ""))

    def test_slots_bounded(self):
        s = JobSlots(2)
        self.assertTrue(s.acquire() and s.acquire())
        self.assertFalse(s.acquire())
        self.assertEqual(s.active, 2)
        s.release()
        self.assertTrue(s.acquire())


class TestHttp(unittest.TestCase):
    def test_auth_enforced_over_http(self):
        with MockWorker(api_key="k1") as w:
            self.assertEqual(requests.post(w.url + "/execute", json={"code": "pass"}).status_code, 401)
            self.assertEqual(requests.post(w.url + "/execute", json={"code": "pass"},
                                           headers={"X-API-Key": "nope"}).status_code, 401)
            ok = requests.post(w.url + "/execute", json={"code": "print(5)"}, headers={"X-API-Key": "k1"})
            self.assertEqual(ok.status_code, 200)
            self.assertEqual(ok.json()["stdout"].strip(), "5")

    def test_health_reports_load(self):
        with MockWorker(api_key="k1") as w:
            h = requests.get(w.url + "/health").json()
            self.assertEqual(h["status"], "ok")
            self.assertIn("active_jobs", h)
            self.assertIn("cpu_count", h)

    def test_busy_returns_503(self):
        with MockWorker(max_jobs=1, extra_delay_s=1.5) as w:
            t = threading.Thread(target=lambda: requests.post(w.url + "/execute", json={"code": "pass"}))
            t.start()
            time.sleep(0.3)
            r = requests.post(w.url + "/execute", json={"code": "pass"})
            t.join()
            self.assertEqual(r.status_code, 503)


class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.log = DecisionLog(os.path.join(self.tmp, "d.jsonl"))

    def make(self, edge, cloud, **kw):
        sched = OffloadingScheduler(rtt_tracker=RttTracker())
        return Dispatcher(sched, WorkerClient(edge.url, "k"), cloud, log=self.log, **kw)

    def test_runs_and_logs_outcome(self):
        with MockWorker(api_key="k") as edge:
            d = self.make(edge, None)
            r = d.run("print('hi')")
            self.assertEqual(r["target"], "edge")
            self.assertEqual(r["worker"]["stdout"].strip(), "hi")
            rec = self.log.read()[0]
            self.assertEqual(rec["target"], "edge")
            self.assertIn("features", rec)
            self.assertEqual(rec["returncode"], 0)

    def test_dispatcher_learns_runtime_from_its_own_runs(self):
        from pipeline.history import RuntimeHistory
        with MockWorker(api_key="k") as edge:
            sched = OffloadingScheduler(rtt_tracker=RttTracker(), history=RuntimeHistory(min_obs=2))
            d = Dispatcher(sched, WorkerClient(edge.url, "k"), None, log=self.log)
            self.assertEqual(d.run("print(1)")["decision_method"], "regression")
            d.run("print(1)")
            third = d.run("print(1)")
            self.assertEqual(third["decision_method"], "regression+history")

    def test_cloud_error_falls_back_to_edge(self):
        with MockWorker(api_key="k") as edge:
            dead = WorkerClient("http://127.0.0.1:9", "k", timeout=1)  # nothing listens on :9
            d = self.make(edge, dead)
            d.scheduler.predictor.fixed_rtt = 0.0  # force a CLOUD-leaning decision path where possible
            d.scheduler.schedule = lambda code, **k: {  # force CLOUD
                "features": {}, "feature_version": 2, "predictions": {}, "decision": "CLOUD",
                "confidence": 0.9, "decision_method": "regression", "code_hash": "x"}
            r = d.run("print(1)")
            self.assertEqual(r["target"], "edge")
            self.assertTrue(r["fallback"].startswith("cloud_error"))
            self.assertEqual(r["worker"]["stdout"].strip(), "1")

    def test_circuit_opens_after_failures_and_skips_cloud(self):
        with MockWorker(api_key="k") as edge:
            dead = WorkerClient("http://127.0.0.1:9", "k", timeout=1)
            d = self.make(edge, dead, breaker=CircuitBreaker(threshold=2, reset_s=60))
            d.scheduler.schedule = lambda code, **k: {
                "features": {}, "feature_version": 2, "predictions": {}, "decision": "CLOUD",
                "confidence": 0.9, "decision_method": "regression", "code_hash": "x"}
            d.run("pass")
            d.run("pass")
            self.assertTrue(d.breaker.is_open)
            self.assertEqual(d.run("pass")["fallback"], "circuit_open")

    def test_breaker_half_opens_after_reset(self):
        now = [0.0]
        b = CircuitBreaker(threshold=1, reset_s=10, clock=lambda: now[0])
        b.record_failure()
        self.assertFalse(b.allow())
        now[0] = 11
        self.assertTrue(b.allow())
        b.record_success()
        self.assertEqual(b.failures, 0)

    def test_edge_failure_raises(self):
        dead = WorkerClient("http://127.0.0.1:9", "k", timeout=1)
        d = Dispatcher(OffloadingScheduler(), dead, None)
        with self.assertRaises(WorkerError):
            d.run("pass")

    def test_exploration_flips_low_confidence_decisions(self):
        import random
        with MockWorker(api_key="k") as edge, MockWorker(api_key="k") as cloud:
            d = self.make(edge, WorkerClient(cloud.url, "k"), epsilon=1.0, rng=random.Random(0))
            d.scheduler.schedule = lambda code, **k: {
                "features": {}, "feature_version": 2, "predictions": {}, "decision": "EDGE",
                "confidence": 0.55, "decision_method": "regression", "code_hash": "x"}
            r = d.run("pass")
            self.assertTrue(r["explored"])
            self.assertEqual(r["target"], "cloud")

    def test_no_exploration_when_confident(self):
        with MockWorker(api_key="k") as edge, MockWorker(api_key="k") as cloud:
            d = self.make(edge, WorkerClient(cloud.url, "k"), epsilon=1.0)
            d.scheduler.schedule = lambda code, **k: {
                "features": {}, "feature_version": 2, "predictions": {}, "decision": "EDGE",
                "confidence": 0.99, "decision_method": "regression", "code_hash": "x"}
            self.assertFalse(d.run("pass")["explored"])

    def test_live_rtt_and_load_from_health(self):
        with MockWorker(api_key="k") as edge, MockWorker(api_key="k", max_jobs=3) as cloud:
            d = self.make(edge, WorkerClient(cloud.url, "k"))
            body = d.refresh_health()
            self.assertIsNotNone(body)
            self.assertIsNotNone(d.scheduler.rtt_tracker.value)
            self.assertEqual(d.cloud_load["active_jobs"], 0)


class TestRttTracker(unittest.TestCase):
    def test_ewma(self):
        t = RttTracker(alpha=0.5)
        self.assertIsNone(t.value)
        t.update(0.1)
        t.update(0.3)
        self.assertAlmostEqual(t.value, 0.2)

    def test_probe_unreachable_returns_none(self):
        self.assertIsNone(RttTracker().probe("http://127.0.0.1:9/health", timeout=0.5))

    def test_scheduler_uses_live_rtt(self):
        slow, fast = RttTracker(initial_s=5.0), RttTracker(initial_s=0.0001)
        code = open(os.path.join(ROOT, "test_scripts", "fib_31.py")).read()
        a = OffloadingScheduler(rtt_tracker=slow).schedule(code)["predictions"]["rtt_s"]
        b = OffloadingScheduler(rtt_tracker=fast).schedule(code)["predictions"]["rtt_s"]
        self.assertAlmostEqual(a, 5.0)
        self.assertLess(b, 0.001)

    def test_explicit_rtt_beats_tracker(self):
        s = OffloadingScheduler(cloud_rtt_ms=50, rtt_tracker=RttTracker(initial_s=9.0))
        self.assertAlmostEqual(s.schedule("print(1)")["predictions"]["rtt_s"], 0.05)


class TestCollectData(unittest.TestCase):
    def test_collects_and_drops_failures(self):
        import subprocess
        tmp = tempfile.mkdtemp()
        out = os.path.join(tmp, "bench.csv")
        with MockWorker(api_key="k") as cloud:
            env = dict(os.environ, CLOUD_WORKER_URL=cloud.url, WORKER_API_KEY="k")
            r = subprocess.run([sys.executable, os.path.join(ROOT, "collect_data.py"), "--repeats", "2",
                                "--only", "fib_2*.py", "--output", out],
                               capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        import pandas as pd
        df = pd.read_csv(out)
        self.assertGreaterEqual(len(df), 2)
        self.assertTrue({"file", "actual_edge_time", "actual_cloud_time", "edge_std", "repeats"} <= set(df.columns))
        meta = json.load(open(os.path.splitext(out)[0] + ".meta.json"))
        self.assertIn("cpu", meta["edge"])

    def test_refuses_without_cloud_url(self):
        import subprocess
        env = {k: v for k, v in os.environ.items() if k != "CLOUD_WORKER_URL"}
        env["HOME"] = tempfile.mkdtemp()
        r = subprocess.run([sys.executable, os.path.join(ROOT, "collect_data.py")],
                           capture_output=True, text=True, env=env, cwd=tempfile.mkdtemp(), timeout=60)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
