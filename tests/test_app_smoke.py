"""Executes app.py top to bottom against a permissive fake Streamlit/Plotly.

It cannot judge the look of the page. It does catch what a refactor most often
breaks: NameErrors, bad f-strings, wrong attribute names, stale imports.
"""
import os
import runpy
import sys
import types
import unittest
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings("ignore")


class Fake:
    """Absorbs any attribute access, call, `with`, or iteration."""
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Fake()

    def __call__(self, *a, **k):
        return Fake()

    def __enter__(self):
        return Fake()

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter([Fake() for _ in range(4)])

    def __bool__(self):
        return False


class State(dict):
    __getattr__ = lambda self, k: self[k] if k in self else (_ for _ in ()).throw(AttributeError(k))  # noqa: E731

    def __setattr__(self, k, v):
        self[k] = v

    def __delattr__(self, k):
        del self[k]


def fake_streamlit(tab, calls):
    st = types.ModuleType("streamlit")
    st.session_state = State(current_tab=tab, theme_mode="dark")
    st.sidebar = Fake()

    def cache(*a, **k):
        if a and callable(a[0]):
            return a[0]
        return lambda fn: fn

    st.cache_resource = st.cache_data = cache

    def markdown(body, *a, **k):
        calls.append(body)

    st.markdown = markdown
    st.columns = lambda spec, **k: [Fake() for _ in range(spec if isinstance(spec, int) else len(spec))]
    st.tabs = lambda names: [Fake() for _ in names]
    st.button = lambda *a, **k: False
    st.toggle = lambda *a, **k: True
    st.slider = lambda label, lo, hi, value=None, **k: value
    st.text_area = lambda *a, value="", **k: value or "print(1)"
    st.file_uploader = lambda *a, **k: None
    st.rerun = lambda: None
    for name in ("set_page_config", "metric", "plotly_chart", "code", "error", "warning", "success",
                 "toast", "caption", "expander", "info"):
        setattr(st, name, Fake())
    return st


def fake_plotly():
    pkg = types.ModuleType("plotly")
    go = Fake()
    pkg.graph_objects = go
    mod = types.ModuleType("plotly.graph_objects")
    mod.__getattr__ = lambda name: Fake()
    return pkg, mod


class TestAppSmoke(unittest.TestCase):
    def run_tab(self, tab):
        calls = []
        saved = {k: sys.modules.get(k) for k in ("streamlit", "plotly", "plotly.graph_objects")}
        pkg, go = fake_plotly()
        sys.modules.update({"streamlit": fake_streamlit(tab, calls), "plotly": pkg, "plotly.graph_objects": go})
        try:
            runpy.run_path(os.path.join(ROOT, "app.py"), run_name="__app__")
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        return "\n".join(c for c in calls if isinstance(c, str))

    def test_overview_renders_computed_numbers_not_old_claims(self):
        html = self.run_tab("overview")
        for stale in ("99.4%", "503", "0.972", "18.60.41.230", "~130ms"):
            self.assertNotIn(stale, html)
        self.assertIn("edge-only", html)

    def test_playground_renders(self):
        self.run_tab("playground")

    def test_endpoints_renders_without_hardcoded_ip(self):
        html = self.run_tab("endpoints")
        self.assertNotIn("18.60.41.230", html)
        self.assertIn("localhost:8000", html)

    def test_telemetry_renders(self):
        self.run_tab("telemetry")


if __name__ == "__main__":
    unittest.main(verbosity=2)
