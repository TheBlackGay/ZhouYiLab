"""八字分布画像契约（bazi-distribution/1.0）。

覆盖：
* 合成命盘：三图百分比手算精确、日干不入十神图分母、平局走 balanced 短语；
* 与内核交叉锁定：天干五行/阴阳逐字对照 ba_zi_web_cli 输出；
* 真实内核集成：1994-12-08 乾造 → 14 点、十神 13 点、每图和恒 100；
* 文案纪律：八字 calibration=in_progress（旺衰/喜忌/格局未上线，D3 三步走），
  画像禁确定性吉凶词、禁"喜用/忌神"暗示；跨图底色以"×"合成、主语"此命"；
* 路由三处一致：manifest、server 分支、前端挂载（与 dlr 同风格）。
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

from astro_distribution import AstroDistributionRequestError  # noqa: E402
from bazi_distribution import (  # noqa: E402
    SCHEMA_VERSION,
    STEM_ELEMENT,
    STEM_YINYANG,
    collect_points,
    compute_bazi_distribution,
    load_reading_config,
)

BAZI_CLI = ROOT / "build" / "examples" / "ba_zi_web_cli"
CONFIG = load_reading_config()


def pillar(stem, branch, stem_ten_god, hidden=()):
    return {
        "stem": stem, "stem_element": STEM_ELEMENT[stem], "stem_ten_god": stem_ten_god,
        "branch": branch,
        "hidden_stems": [{"stem": s, "element": STEM_ELEMENT[s], "ten_god": g} for s, g in hidden],
    }


def synthetic_chart():
    """干支：甲/乙/丙/丁 + 藏干戊、庚 → 五行 木2火2土1金1；
    十神（不含日干）：官、劫、财、印、比(戊) → bijie=2 主导；
    阴阳：positive 甲丙戊庚=4 / negative 乙丁=2。"""
    return {"pillars": {
        "year": pillar("甲", "戌", "七杀", [("戊", "比肩")]),
        "month": pillar("乙", "子", "劫财"),
        "day": pillar("丙", "辰", "比肩"),
        "hour": pillar("丁", "巳", "正财", [("庚", "正印")]),
    }}


def percents(chart):
    return {s["key"]: s["percent"] for s in chart["segments"]}


class BaziDistributionTests(unittest.TestCase):
    def test_synthetic_percents_denominators_and_headline(self):
        result = compute_bazi_distribution(synthetic_chart(), CONFIG)
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["point_basis"]["count"], 6)
        charts = {c["id"]: c for c in result["charts"]}
        # 五行：木2 火2 土1 金1 水0 → 33/33/17/17/0（最大余数先补土金余数），最大并列 → balanced
        self.assertEqual(percents(charts["signs"]),
                         {"木": 33, "火": 33, "土": 17, "金": 17, "水": 0})
        self.assertIsNone(charts["signs"]["dominant"])
        # 十神：点集不含日干丙 → 5 点，bijie=乙+戊=2 主导
        self.assertEqual(charts["gods"]["point_total"], 5)
        self.assertEqual(percents(charts["gods"]),
                         {"bijie": 40, "shishang": 0, "cai": 20, "guan": 20, "yin": 20})
        self.assertEqual(charts["gods"]["dominant"]["key"], "bijie")
        # 阴阳：4:2 → 67/33，positive 主导
        self.assertEqual(percents(charts["polarity"]), {"positive": 67, "negative": 33})
        # 跨图箴言底色：×连接、"此命"主语（无 label 时）
        self.assertEqual(result["summary_zh"], "此命的底色：五气匀停×同气并肩×外放明亮。")
        self.assertIn("此命", charts["polarity"]["headline_zh"])
        for c in result["charts"]:
            self.assertEqual(sum(percents(c).values()), 100)

    def test_label_switches_subject(self):
        result = compute_bazi_distribution(synthetic_chart(), CONFIG, label="样本甲")
        self.assertTrue(result["summary_zh"].startswith("「样本甲」的底色："))

    def test_day_stem_excluded_but_counted_elsewhere(self):
        points = collect_points(synthetic_chart())
        day = [p for p in points if p["point_id"] == "day_stem"]
        self.assertEqual(len(day), 1)
        self.assertIsNone(day[0]["attributes"]["gods"])
        self.assertEqual(day[0]["attributes"]["signs"], "火")

    def test_rejects_unknown_ten_god_and_kernel_element_drift(self):
        bad = synthetic_chart()
        bad["pillars"]["month"]["stem_ten_god"] = "天外飞仙"
        with self.assertRaises(AstroDistributionRequestError):
            compute_bazi_distribution(bad, CONFIG)
        drift = synthetic_chart()
        drift["pillars"]["year"]["stem_element"] = "火"  # 内核若与标准表不符须报错
        with self.assertRaises(AstroDistributionRequestError):
            compute_bazi_distribution(drift, CONFIG)
        with self.assertRaises(AstroDistributionRequestError):
            compute_bazi_distribution({"pillars": {"year": {}}}, CONFIG)

    def test_kernel_cross_lock_real_chart(self):
        if not BAZI_CLI.exists():
            self.skipTest("ba_zi_web_cli 未构建")
        completed = subprocess.run(
            [str(BAZI_CLI)], input=json.dumps(
                {"date": {"year": 1994, "month": 12, "day": 8, "hour": 9, "minute": 5}}),
            capture_output=True, text=True, timeout=30, cwd=ROOT, check=False)
        chart = json.loads(completed.stdout)
        # 标准表逐字交叉：天干五行/阴阳、藏干五行与内核输出一致
        for pos in ("year", "month", "day", "hour"):
            p = chart["pillars"][pos]
            self.assertEqual(STEM_ELEMENT[p["stem"]], p["stem_element"])
            self.assertEqual(STEM_YINYANG[p["stem"]],
                             "positive" if p["stem_yin_yang"] == "阳" else "negative")
            for h in p["hidden_stems"]:
                self.assertEqual(STEM_ELEMENT[h["stem"]], h["element"])
        result = compute_bazi_distribution(chart, CONFIG)
        # 1994-12-08 巳时：干4 + 藏干3+1+3+2=9 → 13 点？（戌3 子1 辰3 巳3=10）→ 14
        self.assertEqual(result["point_basis"]["count"], 14)
        charts = {c["id"]: c for c in result["charts"]}
        self.assertEqual(charts["gods"]["point_total"], 13)  # 不含日干戊
        for c in result["charts"]:
            self.assertEqual(sum(percents(c).values()), 100)
        self.assertTrue(result["summary_zh"].startswith("此命的底色："))

    def test_reading_texts_have_no_auspice_or_favor_claims(self):
        # 八字旺衰/喜忌/格局未上线（D3）：画像既禁吉凶断语，也禁喜用/忌神暗示
        banned = ("主吉", "主凶", "大吉", "必凶", "必胜", "必败", "断曰",
                  "喜用", "忌神", "用神", "身强", "身弱", "从格")
        for chart in CONFIG["charts"].values():
            blob = (chart["title_zh"] + chart["basis_zh"] + chart["balanced_template_zh"]
                    + "".join(chart["readings_zh"].values())
                    + "".join(chart["summary_phrases_zh"].values()))
            for word in banned:
                self.assertNotIn(word, blob, f"{chart['title_zh']} 含禁词 {word}")

    def test_route_wired_everywhere(self):
        manifest = json.loads((ROOT / "config/platform/tools/bazi.json").read_text(encoding="utf-8"))
        self.assertIn("/api/v1/bazi/distribution", {r["path"] for r in manifest["routes"]})
        server = (ROOT / "web" / "server.py").read_text(encoding="utf-8")
        self.assertIn('"/api/v1/bazi/distribution"', server)
        self.assertIn("def run_bazi_distribution", server)
        page = (ROOT / "web" / "bazi.html").read_text(encoding="utf-8")
        self.assertIn('id="bazi-profile-charts"', page)
        self.assertIn("/profile-charts.js", page)
        javascript = (ROOT / "web" / "bazi.js").read_text(encoding="utf-8")
        self.assertIn("/api/v1/bazi/distribution", javascript)


if __name__ == "__main__":
    unittest.main()
