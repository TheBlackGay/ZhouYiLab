"""梅花卦面画像契约（meihua-distribution/1.0，M4）。

覆盖：
* 月令五态表画像侧实现与五张季节标准表逐字一致（与六爻锁表同源）；
* 合成盘（书例盘面）：三图百分比手算精确、和恒 100、× 箴言底色；
* 运行时交叉锁：篡改内核体用旺衰字段必须拒绝出图（漂移即爆炸，不出错图）；
* 真实内核集成：mei_hua_web_cli 书例盘 → 12 点、与内核字段自洽；
* 文案纪律：梅花 pending，禁吉凶断语词；
* 路由一致：manifest、server 分支、前端挂载三处（engine_chart 之外新增
  python_service 路由的登记完整性）。
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

from astro_distribution import AstroDistributionRequestError  # noqa: E402
from meihua_distribution import (  # noqa: E402
    BRANCH_ELEMENT,
    SCHEMA_VERSION,
    compute_meihua_distribution,
    load_reading_config,
    wang_shuai,
)

MEI_HUA_CLI = ROOT / "build" / "examples" / "mei_hua_web_cli"
CONFIG = load_reading_config()

# 书例事实盘的盘面结构字段（与 M1 锁测试同源；旺衰为内核丑月值）
BOOK_PLATE = {
    "schema_version": "meihua-plate/1.0",
    "ba_zi": {"month_command": "丑"},
    "ben_gua": {"code": "101110", "name": "泽火革", "inner": "离", "inner_element": "火",
                "outer": "兑", "outer_element": "金"},
    "hu_gua": {"code": "011111", "name": "天风姤", "inner": "巽", "inner_element": "木",
               "outer": "乾", "outer_element": "金"},
    "bian_gua": {"code": "001110", "name": "泽山咸", "inner": "艮", "inner_element": "土",
                 "outer": "兑", "outer_element": "金"},
    "ti_yong": {"ti": "upper", "yong": "lower", "ti_element": "金", "yong_element": "火",
                "relation": "用克体", "ti_wang_shuai": "相", "yong_wang_shuai": "休"},
}

# 《翼氏大典》五张季节表（与 tests/test_wang_shuai_contract.py 同一权威）
SEASON_TABLES = {
    "木": {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"},
    "火": {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"},
    "土": {"土": "旺", "金": "相", "火": "休", "木": "囚", "水": "死"},
    "金": {"金": "旺", "水": "相", "土": "休", "火": "囚", "木": "死"},
    "水": {"水": "旺", "木": "相", "金": "休", "土": "囚", "火": "死"},
}


def percents(chart):
    return {s["key"]: s["percent"] for s in chart["segments"]}


class MeihuaDistributionTests(unittest.TestCase):
    def test_season_table_matches_canonical(self):
        for branch, element in BRANCH_ELEMENT.items():
            table = SEASON_TABLES[element]
            for elem, expected in table.items():
                self.assertEqual(wang_shuai(elem, branch), expected,
                                 f"{branch}月（{element}令）{elem}应为{expected}")

    def test_book_plate_synthetic_percents_and_headline(self):
        result = compute_meihua_distribution(BOOK_PLATE, CONFIG)
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["point_basis"]["count"], 12)
        charts = {c["id"]: c for c in result["charts"]}
        # 五行：金3(兑×2乾) 木1 火1 土1 水0 → 17/17/16/50/0，金主导
        self.assertEqual(percents(charts["signs"]),
                         {"木": 17, "火": 17, "土": 16, "金": 50, "水": 0})
        self.assertEqual(charts["signs"]["dominant"]["key"], "金")
        # 旺衰（丑月土令）：相3(金) 旺1(艮土) 休1(离火) 囚1(巽木) 死0 → 17/50/17/16/0
        self.assertEqual(percents(charts["states"]),
                         {"旺": 17, "相": 50, "休": 17, "囚": 16, "死": 0})
        self.assertEqual(charts["states"]["dominant"]["key"], "相")
        # 本卦 101110：阳4 阴2 → 67/33
        self.assertEqual(percents(charts["polarity"]), {"positive": 67, "negative": 33})
        for c in result["charts"]:
            self.assertEqual(sum(percents(c).values()), 100)
        self.assertEqual(result["summary_zh"], "此卦的底色：清明肃断×得势上行×显动于外。")

    def test_cross_lock_rejects_engine_drift(self):
        drifted = json.loads(json.dumps(BOOK_PLATE))
        drifted["ti_yong"]["ti_wang_shuai"] = "旺"  # 伪装内核表漂移
        with self.assertRaises(AstroDistributionRequestError) as ctx:
            compute_meihua_distribution(drifted, CONFIG)
        self.assertIn("交叉锁", str(ctx.exception))

    def test_dirty_plate_rejected(self):
        with self.assertRaises(AstroDistributionRequestError):
            compute_meihua_distribution({"schema_version": "other/0.0"}, CONFIG)
        missing = json.loads(json.dumps(BOOK_PLATE))
        del missing["hu_gua"]["outer_element"]
        with self.assertRaises(AstroDistributionRequestError):
            compute_meihua_distribution(missing, CONFIG)
        bad_code = json.loads(json.dumps(BOOK_PLATE))
        bad_code["ben_gua"]["code"] = "10111x"
        with self.assertRaises(AstroDistributionRequestError):
            compute_meihua_distribution(bad_code, CONFIG)

    def test_real_kernel_plate_integration(self):
        if not MEI_HUA_CLI.exists():
            self.skipTest("mei_hua_web_cli 未构建")
        completed = subprocess.run(
            [str(MEI_HUA_CLI)], input=json.dumps(
                {"mode": "time", "calendar": "lunar",
                 "date": {"year": 1916, "month": 12, "day": 17, "hour": 16}}),
            capture_output=True, text=True, timeout=30, cwd=ROOT, check=False)
        plate = json.loads(completed.stdout)
        result = compute_meihua_distribution(plate, CONFIG)  # 交叉锁在内部生效
        self.assertEqual(result["point_basis"]["count"], 12)
        for c in result["charts"]:
            self.assertEqual(sum(percents(c).values()), 100)
        self.assertTrue(result["summary_zh"].startswith("此卦的底色："))
        self.assertEqual(result["charts"][0]["dominant"]["key"], "金")

    def test_reading_texts_have_no_auspice_claims(self):
        banned = ("主吉", "主凶", "大吉", "必凶", "必胜", "必败", "断曰",
                  "用神", "喜用", "忌神", "吉凶悔吝")
        for chart in CONFIG["charts"].values():
            blob = (chart["title_zh"] + chart["basis_zh"] + chart["balanced_template_zh"]
                    + "".join(chart["readings_zh"].values())
                    + "".join(chart["summary_phrases_zh"].values())
                    + "".join(chart["dominant_templates_zh"].values()))
            for word in banned:
                self.assertNotIn(word, blob, f"{chart['title_zh']} 含禁词 {word}")

    def test_route_wired_everywhere(self):
        manifest = json.loads((ROOT / "config/platform/tools/mei_hua.json").read_text(encoding="utf-8"))
        self.assertIn("/api/v1/mei-hua/distribution", {r["path"] for r in manifest["routes"]})
        server = (ROOT / "web" / "server.py").read_text(encoding="utf-8")
        self.assertIn('"/api/v1/mei-hua/distribution"', server)
        self.assertIn("def run_meihua_distribution", server)
        page = (ROOT / "web" / "meihua.html").read_text(encoding="utf-8")
        self.assertIn('id="mh-profile-charts"', page)
        self.assertIn("/profile-charts.js", page)
        javascript = (ROOT / "web" / "meihua.js").read_text(encoding="utf-8")
        self.assertIn("/api/v1/mei-hua/distribution", javascript)


if __name__ == "__main__":
    unittest.main()
