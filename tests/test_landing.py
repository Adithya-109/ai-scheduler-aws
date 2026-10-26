import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LP = os.path.join(ROOT, "landing-page")


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as fh:
        return fh.read()


class LandingPage(unittest.TestCase):
    def test_no_unreproduced_claims(self):
        html = read("landing-page", "index.html")
        for stale in ("99.4", "44.7", "Random Forest", "1.84ms", "109ms", "ap-south-2", "100%"):
            self.assertNotIn(stale, html)

    def test_launch_goes_straight_to_the_dashboard_and_light_is_default(self):
        html, js = read("landing-page", "index.html"), read("landing-page", "script.js")
        self.assertIn("localhost:8501/?tab=playground", html)
        self.assertIn('data-theme="light"', html)
        self.assertIn("let isLightMode = true", js)

    def test_app_defaults(self):
        app = read("app.py")
        self.assertIn('("current_tab", "playground")', app)
        self.assertIn('("theme_mode", "light")', app)

    def test_done_banner_is_short_and_readable(self):
        import re
        src = read("ui", "execution.py")
        secs = float(re.search(r"doneBanner ([\d.]+)s", src).group(1))
        self.assertLessEqual(secs, 2.0)
        self.assertNotIn("MISSION ACCOMPLISHED", src)
        self.assertIn("var(--surface-card)", src)  # follows the theme instead of a fixed dark overlay


if __name__ == "__main__":
    unittest.main()
