"""Property and regression tests for the log-space feature extractor."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline.feature_extractor import FEATURE_COLUMNS, CodeFeatureExtractor  # noqa: E402

ex = CodeFeatureExtractor()


def cx(code):
    return ex.analyze(code)["estimated_complexity"]


def script(name):
    with open(os.path.join(ROOT, "test_scripts", name), encoding="utf-8") as fh:
        return fh.read()


class TestMonotonic(unittest.TestCase):
    def test_bigger_range_never_cheaper(self):
        prev = -1
        for n in (10, 1000, 10**5, 10**7, 10**9, 10**12):
            c = cx(f"s=0\nfor i in range({n}):\n    s+=i")
            self.assertGreaterEqual(c, prev)
            prev = c

    def test_nesting_multiplies(self):
        a = cx("for i in range(100):\n  pass")
        b = cx("for i in range(100):\n  for j in range(100):\n    pass")
        c = cx("for i in range(100):\n  for j in range(100):\n    for k in range(100):\n      pass")
        self.assertGreater(b, a + 1.5)
        self.assertGreater(c, b + 1.5)

    def test_sequential_loops_add_not_multiply(self):
        one = cx("for i in range(10**6):\n  pass")
        two = cx("for i in range(10**6):\n  pass\nfor j in range(10**6):\n  pass")
        self.assertLess(two - one, 0.5)

    def test_cost_comes_from_loop_bound_not_unrelated_constants(self):
        self.assertLess(cx("for i in range(10):\n  x = 10**18"), cx("for i in range(10**6):\n  x = 1"))

    def test_variable_bound_resolved(self):
        self.assertAlmostEqual(cx("n = 100000\nfor i in range(n):\n  pass"),
                               cx("for i in range(100000):\n  pass"), delta=0.2)

    def test_triangular_loop_cheaper_than_square(self):
        tri = cx("for i in range(1000):\n  for j in range(i):\n    pass")
        sq = cx("for i in range(1000):\n  for j in range(1000):\n    pass")
        self.assertLess(tri, sq)

    def test_no_overflow_on_absurd_nests(self):
        code = "".join("  " * d + "for i%d in range(10**9):\n" % d for d in range(12)) + "  " * 12 + "pass"
        f = ex.analyze(code)
        self.assertLessEqual(f["estimated_complexity"], 12.0)
        self.assertEqual(f["max_loop_depth"], 12)

    def test_huge_literals_do_not_raise(self):
        f = ex.analyze("x = 10**400\nfor i in range(3):\n  y = 1e308 * 1e308")
        self.assertNotIn("error", f)


class TestRecursionAndFunctions(unittest.TestCase):
    FIB = "def fib(n):\n  return n if n<2 else fib(n-1)+fib(n-2)\nprint(fib({}))"

    def test_exponential_recursion_grows_with_argument(self):
        vals = [cx(self.FIB.format(n)) for n in (10, 20, 30, 35)]
        self.assertEqual(vals, sorted(vals))
        self.assertGreater(vals[-1] - vals[0], 5)

    def test_recursion_flag(self):
        self.assertEqual(ex.analyze(self.FIB.format(5))["has_recursion"], 1)
        self.assertEqual(ex.analyze("print(1)")["has_recursion"], 0)

    def test_memoised_recursion_is_linear(self):
        memo = ("from functools import lru_cache\n@lru_cache(None)\ndef fib(n):\n"
                "  return n if n<2 else fib(n-1)+fib(n-2)\nprint(fib(35))")
        self.assertLess(cx(memo), cx(self.FIB.format(35)) - 3)

    def test_function_cost_counted_at_call_site(self):
        defined_only = cx("def f():\n  for i in range(10**6):\n    pass")
        called = cx("def f():\n  for i in range(10**6):\n    pass\nf()")
        self.assertGreater(called, defined_only + 3)

    def test_function_called_twice_costs_more(self):
        body = "def f():\n  for i in range(10**6):\n    pass\n"
        self.assertGreater(cx(body + "f()\nf()"), cx(body + "f()"))

    def test_argument_drives_function_cost(self):
        body = "def work(n):\n  for i in range(n):\n    pass\n"
        self.assertGreater(cx(body + "work(10**7)"), cx(body + "work(10**3)") + 3)


class TestNumpyAndTime(unittest.TestCase):
    MM = "import numpy as np\nA=np.random.rand({0},{0})\nB=np.random.rand({0},{0})\nC=np.dot(A,B)"

    def test_matmul_scales_with_size(self):
        self.assertGreater(cx(self.MM.format(2000)), cx(self.MM.format(200)) + 2)

    def test_matmul_uses_blas_counter(self):
        f = ex.analyze(self.MM.format(1000))
        self.assertGreater(f["log_blas_flops"], 8.5)
        self.assertEqual(f["has_heavy_lib"], 1)

    def test_array_size_flows_through_assignment(self):
        small = "import numpy as np\nn=1000\nx=np.random.rand(n)\ny=np.sort(x)"
        big = "import numpy as np\nn=10000000\nx=np.random.rand(n)\ny=np.sort(x)"
        self.assertGreater(cx(big), cx(small) + 2)

    def test_from_numpy_import_dot(self):
        f = ex.analyze("from numpy import dot\nfrom numpy.random import rand\nA=rand(500,500)\ndot(A,A)")
        self.assertEqual(f["has_heavy_lib"], 1)

    def test_busy_wait_read_as_wall_clock(self):
        code = "import time\nt=time.perf_counter()\nwhile time.perf_counter()-t < 2.0:\n    pass"
        f = ex.analyze(code)
        self.assertEqual(f["time_bound_s"], 2.0)
        self.assertGreater(f["estimated_complexity"], 7)

    def test_sleep_recorded(self):
        self.assertEqual(ex.analyze("import time\ntime.sleep(3)")["time_bound_s"], 3.0)


class TestRobustness(unittest.TestCase):
    def test_all_repo_scripts_analyse_without_error(self):
        for f in sorted(os.listdir(os.path.join(ROOT, "test_scripts"))):
            if f.endswith(".py"):
                r = ex.analyze(script(f))
                self.assertNotIn("error", r, f)
                self.assertEqual(r["analysis_degraded"], 0, f)
                for c in FEATURE_COLUMNS:
                    self.assertIn(c, r)

    def test_deeply_nested_expression_degrades_not_crashes(self):
        code = "x = " + "(" * 150 + "1" + ")" * 150
        f = ex.analyze(code)
        self.assertTrue("error" in f or "estimated_complexity" in f)

    def test_budget_guard_on_pathological_source(self):
        code = "def f(n):\n" + "".join(f"  g{i}(n)\n" for i in range(50)) + "\n".join(
            f"def g{i}(n):\n  f(n)" for i in range(50)) + "\nf(3)"
        self.assertNotIn("error", ex.analyze(code))

    def test_null_bytes_and_syntax_errors_return_error(self):
        self.assertIn("error", ex.analyze("x = \x00"))
        self.assertIn("error", ex.analyze("def ("))

    def test_does_not_execute_code(self):
        marker = os.path.join(ROOT, ".should_not_exist")
        ex.analyze(f"open({marker!r}, 'w').write('x')")
        self.assertFalse(os.path.exists(marker))

    def test_fresh_state_per_call(self):
        ex.analyze("n=10**9\nfor i in range(n):\n  pass")
        self.assertLess(ex.analyze("print(1)")["estimated_complexity"], 2)

    def test_dataset_families_are_distinguishable(self):
        a = cx(script("sort_100000.py"))
        b = cx(script("sort_2000000.py"))
        self.assertGreater(b, a + 1)
        self.assertGreater(cx(script("fib_35.py")), cx(script("fib_20.py")) + 2)
        self.assertGreater(cx(script("numpy_matmul_3000.py")), cx(script("numpy_matmul_200.py")) + 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestGeneratorSizes(unittest.TestCase):
    """rng = np.random.default_rng(...); rng.random((n, n)) must size arrays like np.random.rand does."""

    @staticmethod
    def feats(code):
        from pipeline.feature_extractor import CodeFeatureExtractor
        return CodeFeatureExtractor().analyze(code)

    def test_matmul_cost_grows_with_generator_array_size(self):
        tpl = "import numpy as np\nrng = np.random.default_rng(0)\nA = rng.random(({n}, {n}))\nB = A @ A\n"
        small, big = self.feats(tpl.format(n=500)), self.feats(tpl.format(n=3000))
        self.assertGreater(big["log_blas_flops"], small["log_blas_flops"] + 2.0)  # (3000/500)^3 ~ 2.3 decades

    def test_matches_legacy_rand_spelling(self):
        gen = self.feats("import numpy as np\nrng = np.random.default_rng(0)\nA = rng.random((800, 800))\nB = A @ A\n")
        old = self.feats("import numpy as np\nA = np.random.rand(800, 800)\nB = A @ A\n")
        self.assertAlmostEqual(gen["log_blas_flops"], old["log_blas_flops"], places=6)

    def test_fft_and_elementwise_scale(self):
        fft = "import numpy as np\nrng = np.random.default_rng(1)\nx = rng.random(2 ** {n})\ny = np.fft.rfft(x)\n"
        self.assertGreater(self.feats(fft.format(n=23))["log_numpy_elems"], self.feats(fft.format(n=18))["log_numpy_elems"] + 1)
        ew = "import numpy as np\nrng = np.random.default_rng(1)\nx = rng.random({n})\ny = np.sqrt(x * x + 1.0)\n"
        self.assertGreater(self.feats(ew.format(n=30_000_000))["estimated_complexity"],
                           self.feats(ew.format(n=1_000_000))["estimated_complexity"])

    def test_unrelated_object_named_like_a_generator_is_not_numpy(self):
        code = "class R:\n    def random(self, n):\n        return n\nrng = R()\nx = rng.random(10 ** 7)\n"
        self.assertLess(self.feats(code)["log_numpy_elems"], 3.0)

    def test_svd_and_eigh_scale(self):
        tpl = "import numpy as np\nrng = np.random.default_rng(0)\nA = rng.random(({n}, {n}))\ns = np.linalg.{f}(A)\n"
        for f in ("svd", "eigvalsh"):
            self.assertGreater(self.feats(tpl.format(n=1200, f=f))["log_blas_flops"],
                               self.feats(tpl.format(n=300, f=f))["log_blas_flops"] + 1.0)
