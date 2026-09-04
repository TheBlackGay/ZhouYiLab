import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
PAGES = {
    "index.html": ("紫微斗数", ["十二宫", "结构解读", "运限", "时间校正"]),
    "qimen.html": ("奇门遁甲", ["九宫盘", "断盘线索", "解读素材"]),
    "bazi.html": ("八字", ["四柱命盘", "大运"]),
}
RESEARCH_PAGES = ("blind-review.html", "ai-review.html")


class WebNavigationContractTests(unittest.TestCase):
    def test_main_pages_use_shared_sticky_two_level_navigation(self):
        for filename, (current_page, secondary_tabs) in PAGES.items():
            with self.subTest(filename=filename):
                html = (WEB_ROOT / filename).read_text(encoding="utf-8")
                self.assertIn('href="/app-shell.css"', html)
                self.assertIn('class="app-navigation"', html)
                self.assertIn('class="primary-tabs"', html)
                self.assertIn('class="secondary-bar"', html)
                current = re.findall(r'<a[^>]+aria-current="page"[^>]*>([^<]+)</a>', html)
                self.assertIn(current_page, current)
                for label in secondary_tabs:
                    self.assertEqual(1, len(re.findall(rf">{label}</button>", html)))

    def test_shared_shell_keeps_navigation_sticky_and_scrollable(self):
        css = (WEB_ROOT / "app-shell.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.app-navigation\s*\{[^}]*position:\s*sticky")
        self.assertIn(".primary-tabs", css)
        self.assertIn(".secondary-tabs", css)
        self.assertIn("overflow-x: auto", css)

    def test_research_pages_keep_global_navigation_and_research_tabs(self):
        for filename in RESEARCH_PAGES:
            with self.subTest(filename=filename):
                html = (WEB_ROOT / filename).read_text(encoding="utf-8")
                self.assertIn('href="/app-shell.css"', html)
                self.assertIn('class="app-navigation"', html)
                self.assertIn('aria-label="命理类型"', html)
                self.assertNotIn('href="/blind-review.html"', html)
                self.assertNotIn('href="/ai-review.html"', html)

    def test_experimental_research_links_are_hidden_from_main_navigation(self):
        for filename in PAGES:
            html = (WEB_ROOT / filename).read_text(encoding="utf-8")
            self.assertNotIn('href="/blind-review.html"', html)
            self.assertNotIn('href="/ai-review.html"', html)

    def test_navigation_centering_and_skip_links_are_loaded(self):
        javascript = (WEB_ROOT / "navigation.js").read_text(encoding="utf-8")
        self.assertIn("centerNavigationItem", javascript)
        self.assertIn("prefers-reduced-motion", javascript)
        for filename in PAGES:
            html = (WEB_ROOT / filename).read_text(encoding="utf-8")
            self.assertIn('class="skip-link"', html)
            self.assertIn('src="/navigation.js"', html)


if __name__ == "__main__":
    unittest.main()
