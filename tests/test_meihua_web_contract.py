"""梅花易数 M2 平台接入契约：注册表路由、页面接线、导航、文档一致性。

风格对齐 test_dlr/astro 的"三处一致"测试：清单声明、注册表分发、前端 fetch
与页面/文档/README 全链路核对（无 server 起进程，路由由注册表驱动天然零分支）。
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

from tool_registry import load_tool_registry  # noqa: E402

REGISTRY = load_tool_registry(ROOT)


class MeiHuaPlatformWiringTests(unittest.TestCase):
    def test_registry_routes_plates(self):
        binding = REGISTRY.resolve("POST", "/api/v1/mei-hua/plates")
        self.assertIsNotNone(binding, "engine_chart 路由未由清单注册")
        manifest, route = binding
        self.assertEqual(manifest.id, "mei_hua")
        self.assertEqual(route.handler, "engine_chart")
        self.assertEqual(manifest.calibration_status, "pending")
        self.assertEqual(manifest.rule_profile_version, "meihua-rules/0.1")
        self.assertEqual(manifest.engine_path(ROOT).name, "mei_hua_web_cli")

    def test_health_and_calibration_expose_meihua(self):
        flags = REGISTRY.health_flags(ROOT)
        self.assertIn("mei_hua_cli_available", flags)
        self.assertIn("mei_hua", REGISTRY.calibration_map())
        self.assertEqual(REGISTRY.calibration_map()["mei_hua"]["calibration_status"], "pending")

    def test_page_and_frontend_wired(self):
        page = (ROOT / "web" / "meihua.html").read_text(encoding="utf-8")
        javascript = (ROOT / "web" / "meihua.js").read_text(encoding="utf-8")
        self.assertIn('id="meihua-form"', page)
        self.assertIn('id="plate-grid"', page)
        self.assertIn('id="tiyong-card"', page)
        self.assertIn('id="casting-summary"', page)
        self.assertIn('name="mode" value="time"', page)
        self.assertIn('name="mode" value="numbers"', page)
        self.assertIn('name="calendar" value="lunar"', page)
        self.assertIn('id="leap-month"', page)
        self.assertIn("/api/v1/mei-hua/plates", javascript)
        # pending 边界声明上页面
        self.assertIn("pending", page)
        self.assertIn("不构成吉凶", page)

    def test_navigation_contains_meihua_everywhere(self):
        for name in ("index.html", "qimen.html", "bazi.html", "liu-yao.html",
                     "da-liu-ren.html", "astro.html", "meihua.html"):
            with self.subTest(page=name):
                html = (ROOT / "web" / name).read_text(encoding="utf-8")
                self.assertIn('href="/meihua.html"', html)

    def test_docs_and_readme_consistent(self):
        doc = (ROOT / "docs" / "梅花易数HTTP接口文档.md").read_text(encoding="utf-8")
        self.assertIn("/api/v1/mei-hua/plates", doc)
        self.assertIn("十五分界", doc)
        self.assertIn("meihua-plate/1.0", doc)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("/api/v1/mei-hua/plates", readme)
        self.assertIn("meihua.html", readme)
        self.assertIn("梅花易数", readme.split("## 算法校准状态", 1)[1].split("\n## ", 1)[0])

    def test_manifest_matches_builtin_shape(self):
        external = json.loads((ROOT / "config/platform/tools/mei_hua.json").read_text(encoding="utf-8"))
        self.assertEqual(external["api_prefixes"], ["/api/v1/mei-hua/"])
        self.assertEqual(external["pages"], ["meihua.html"])
        self.assertEqual(external["routes"][0]["options"]["timeout_message"], "梅花起卦计算超时")


if __name__ == "__main__":
    unittest.main()
