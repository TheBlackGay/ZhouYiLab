"""紫微分布画像契约（ziwei-distribution/1.0）+ 服务端点接线。"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

from astro_distribution import AstroDistributionRequestError  # noqa: E402
from ziwei_distribution import (  # noqa: E402
    SCHEMA_VERSION,
    compute_ziwei_distribution,
    load_reading_config,
)

ZIWEI_CLI = ROOT / "build" / "examples" / "zi_wei_web_cli"
CONFIG = load_reading_config()


def synthetic():
    elements = {"紫微": ("土", "阴"), "天机": ("木", "阴"), "太阳": ("火", "阳"),
                "武曲": ("金", "阳"), "天同": ("水", "阴"), "廉贞": ("火", "阴"),
                "天府": ("土", "阳"), "太阴": ("水", "阴"), "贪狼": ("木", "阳"),
                "巨门": ("水", "阴"), "天相": ("水", "阳"), "天梁": ("土", "阴"),
                "七杀": ("金", "阴"), "破军": ("水", "阴"), "左辅": ("木", "阳"),
                "火星": ("火", "阳")}
    degrees = ["庙", "旺", "得", "平", "陷", "利", "庙", "旺", "庙", "得", "平", "陷", "旺", "庙"]
    temperament = [{"name": n, "group": "zhu_xing", "element": e, "polarity": y}
                   for n, (e, y) in elements.items()]
    palaces = [{"zhu_xing": [{"name": n, "liang_du": d}],
                "fu_xing": ["左辅"] if i == 0 else [], "sha_xing": ["火星"] if i == 1 else []}
               for i, (n, d) in enumerate(zip(list(elements)[:14], degrees))]
    return {"palaces": palaces}, {"star_temperament": temperament}


class ZiweiDistributionTests(unittest.TestCase):
    def test_schema_percents_and_denominators(self):
        chart, symbols = synthetic()
        result = compute_ziwei_distribution(chart, symbols, CONFIG, label="甲")
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["point_basis"]["count"], 16)
        totals = {}
        for c in result["charts"]:
            self.assertEqual(sum(s["percent"] for s in c["segments"]), 100, c["id"])
            self.assertTrue(c["headline_zh"].startswith("「甲」"))
            self.assertTrue(c["reading_zh"].strip())
            totals[c["id"]] = c["point_total"]
        self.assertEqual(totals["light"], 14, "明暗图分母必须是主星亮度")
        self.assertEqual(totals["temperament"], 16)
        self.assertIn("底色", result["summary_zh"])

    def test_missing_temperament_rejected(self):
        chart, _ = synthetic()
        with self.assertRaises(AstroDistributionRequestError):
            compute_ziwei_distribution(chart, {}, CONFIG)

    @unittest.skipUnless(ZIWEI_CLI.exists(), "zi_wei_web_cli 未构建")
    def test_real_chart_end_to_end(self):
        def cli(request):
            r = subprocess.run([str(ZIWEI_CLI)], input=json.dumps(request),
                               capture_output=True, text=True, timeout=30, cwd=ROOT)
            return json.loads(r.stdout)
        chart = cli({"operation": "chart", "birth": {"year": 1994, "month": 12, "day": 8,
                     "hour": 9, "minute": 5, "second": 0, "gender": "male"},
                     "time_correction": {"mode": "standard_time"}})
        symbols = cli({"operation": "symbols"})
        result = compute_ziwei_distribution(chart, symbols, load_reading_config())
        basis = result["point_basis"]["count"]
        self.assertGreaterEqual(basis, 14, "主星必须在场")
        self.assertLessEqual(basis, 28, "presence 不超过主+辅+煞全集")
        self.assertEqual({c["id"] for c in result["charts"]},
                         {"temperament", "polarity", "light"})
        for c in result["charts"]:
            self.assertEqual(sum(s["percent"] for s in c["segments"]), 100)
            self.assertLessEqual(c["point_total"], basis)

    def test_endpoint_wired(self):
        server = (ROOT / "web/server.py").read_text(encoding="utf-8")
        self.assertIn('"/api/v1/ziwei/distribution"', server)
        self.assertIn("def run_ziwei_distribution", server)
        manifest = json.loads((ROOT / "config/platform/tools/ziwei.json").read_text(encoding="utf-8"))
        self.assertIn("/api/v1/ziwei/distribution",
                      {r["path"] for r in manifest["routes"]})
        page = (ROOT / "web/index.html").read_text(encoding="utf-8")
        app = (ROOT / "web/app.js").read_text(encoding="utf-8")
        self.assertIn('id="ziwei-profile-charts"', page)
        self.assertIn("/profile-charts.js", page)
        self.assertIn("/api/v1/ziwei/distribution", app)


if __name__ == "__main__":
    unittest.main()
