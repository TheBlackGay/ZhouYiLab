"""大六壬分布画像契约（dlr-distribution/1.0）。

覆盖：
* 合成十二宫盘：三图百分比手算精确、遁干图分母自动剔除旬空位；
* 五行/阴阳归类与内核标准表交叉一致（子水丑土……、阳支子寅辰午申戌）；
* 文案纪律：六壬 calibration=pending，画像只描述"课面气象"，禁断语词；
* 真实内核集成：astro/六壬 CLI 课盘 → 12 点、和恒 100；
* 路由三处一致：manifest、server 分支、前端挂载。
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

from astro_distribution import AstroDistributionRequestError  # noqa: E402
from dlr_distribution import (  # noqa: E402
    BRANCH_ELEMENT,
    SCHEMA_VERSION,
    STEM_ELEMENT,
    YANG_BRANCHES,
    collect_plate_points,
    compute_dlr_distribution,
    load_reading_config,
)

DLR_CLI = ROOT / "build" / "examples" / "da_liu_ren_web_cli"
CONFIG = load_reading_config()

# 合成盘：上神 = 子丑寅卯辰巳午未申酉戌亥（全覆盖十二支）；遁干只给 10 宫（2 空亡）
def synthetic_chart():
    upper = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    stems = ["甲", "乙", "丙", "丁", "戊", "", "己", "庚", "辛", "壬", "癸", ""]
    return {"tian_di_pan": [
        {"position": p, "tian_pan": u, "dun_gan": s, "shen_jiang": "贵人"}
        for p, u, s in zip(upper, upper, stems)]}


def percents(chart):
    return {s["key"]: s["percent"] for s in chart["segments"]}


class DlrDistributionTests(unittest.TestCase):
    def test_kernel_branch_stem_tables_standard(self):
        # 与内核 WuXingUtils.branchFiveElements 的标准口径一致
        self.assertEqual(BRANCH_ELEMENT["子"], "水")
        self.assertEqual(BRANCH_ELEMENT["卯"], "木")
        self.assertEqual(BRANCH_ELEMENT["申"], "金")
        self.assertEqual(STEM_ELEMENT["甲"], "木")
        self.assertEqual(YANG_BRANCHES, {"子", "寅", "辰", "午", "申", "戌"})

    def test_synthetic_percents_and_denominators(self):
        result = compute_dlr_distribution(synthetic_chart(), CONFIG, label="问事人")
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["point_basis"]["count"], 12)
        charts = {c["id"]: c for c in result["charts"]}
        # 上神五行：水2(子亥) 木2(寅卯) 火2(巳午) 土4(丑辰未戌) 金2(申酉) → /12
        self.assertEqual(percents(charts["signs"]),
                         {"木": 17, "火": 17, "土": 33, "金": 17, "水": 16})
        # 阴阳：阳支 子寅辰午申戌=6 → 与阴各半
        self.assertEqual(percents(charts["polarity"]), {"positive": 50, "negative": 50})
        self.assertIn("各半", charts["polarity"]["headline_zh"])
        # 遁干 10 点：木2 火2 土1 金2 水2 + 戊己土 1 → 甲乙木2 丙丁火2 戊土1 庚辛金2 壬癸水2
        self.assertEqual(charts["stems"]["point_total"], 10)
        for c in result["charts"]:
            self.assertEqual(sum(percents(c).values()), 100)
        self.assertTrue(result["summary_zh"].startswith("「问事人」气象"))

    def test_real_chart_via_kernel(self):
        if not DLR_CLI.exists():
            self.skipTest("da_liu_ren_web_cli 未构建")
        completed = subprocess.run(
            [str(DLR_CLI)], input=json.dumps({"calendar": "solar",
             "date": {"year": 2025, "month": 11, "day": 3, "hour": 16}}),
            capture_output=True, text=True, timeout=30, cwd=ROOT, check=False)
        chart = json.loads(completed.stdout)
        result = compute_dlr_distribution(chart, CONFIG)
        self.assertEqual(result["point_basis"]["count"], 12)
        for c in result["charts"]:
            self.assertEqual(sum(s["percent"] for s in c["segments"]), 100)
        points = collect_plate_points(chart)
        self.assertEqual([p["attributes"]["signs"] for p in points],
                         [BRANCH_ELEMENT[x["tian_pan"]] for x in chart["tian_di_pan"]])

    def test_error_on_broken_plate(self):
        with self.assertRaises(AstroDistributionRequestError):
            compute_dlr_distribution({"tian_di_pan": []}, CONFIG)
        bad = synthetic_chart()
        bad["tian_di_pan"][0]["tian_pan"] = "鼠"
        with self.assertRaises(AstroDistributionRequestError):
            compute_dlr_distribution(bad, CONFIG)

    def test_reading_texts_have_no_auspice_claims(self):
        # 六壬 pending：画像文案禁确定性吉凶词
        banned = ("主吉", "主凶", "大吉", "必凶", "必胜", "必败", "断曰")
        for chart in CONFIG["charts"].values():
            blob = chart["title_zh"] + chart["basis_zh"] + chart["balanced_template_zh"]
            blob += "".join(chart["readings_zh"].values()) + "".join(chart["summary_phrases_zh"].values())
            for word in banned:
                self.assertNotIn(word, blob, f"{chart['title_zh']} 含断语词 {word}")

    def test_route_wired_everywhere(self):
        manifest = json.loads((ROOT / "config/platform/tools/da_liu_ren.json").read_text(encoding="utf-8"))
        self.assertIn("/api/v1/da-liu-ren/distribution", {r["path"] for r in manifest["routes"]})
        server = (ROOT / "web" / "server.py").read_text(encoding="utf-8")
        self.assertIn('"/api/v1/da-liu-ren/distribution"', server)
        self.assertIn("def run_dlr_distribution", server)
        page = (ROOT / "web" / "da-liu-ren.html").read_text(encoding="utf-8")
        self.assertIn('id="dlr-profile-charts"', page)
        self.assertIn("/profile-charts.js", page)
        javascript = (ROOT / "web" / "da-liu-ren.js").read_text(encoding="utf-8")
        self.assertIn("/api/v1/da-liu-ren/distribution", javascript)


if __name__ == "__main__":
    unittest.main()
