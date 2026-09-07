import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PAGES = ("index.html", "qimen.html", "bazi.html", "liu-yao.html", "da-liu-ren.html")


class UiFoundationContractTests(unittest.TestCase):
    def test_workspace_pages_load_shared_ui_foundation_before_page_styles(self):
        for name in PAGES:
            html = (ROOT / "web" / name).read_text(encoding="utf-8")
            foundation = html.index('href="/ui-foundation.css"')
            app_shell = html.index('href="/app-shell.css"')
            self.assertLess(foundation, app_shell, name)

    def test_foundation_contains_accessibility_and_responsive_contract(self):
        css = (ROOT / "web" / "ui-foundation.css").read_text(encoding="utf-8")
        for fragment in ("[hidden]", "focus-visible", "prefers-reduced-motion", "font-size: 16px"):
            self.assertIn(fragment, css)

    def test_workspace_pages_have_skip_link_and_viewport_meta(self):
        for name in PAGES:
            html = (ROOT / "web" / name).read_text(encoding="utf-8")
            self.assertIn('name="viewport"', html, name)
            self.assertIn('class="skip-link"', html, name)


if __name__ == "__main__":
    unittest.main()
