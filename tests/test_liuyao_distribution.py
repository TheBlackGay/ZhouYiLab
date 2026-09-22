"""六爻分布画像契约（liuyao-distribution/1.0）。

覆盖：
* 真实内核集成：乾宫卦六爻（2025-02-12 寅月）逐爻 wangShuai 与 DEF-4 修复后
  月令表交叉锁定；三图百分比手算精确、每图和恒 100；
* 合成盘：三向平局走 balanced 短语（"五亲并济"）；
* 脏数据守卫：缺爻、旺衰"未知"（口径漂移信号）、表外六亲均须报错；
* 文案纪律：六爻 calibration=pending，禁吉凶断语与"用神"暗示；
* 跨图箴言底色：×连接、主语"此卦"；
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
from liuyao_distribution import (  # noqa: E402
    SCHEMA_VERSION,
    compute_liuyao_distribution,
    load_reading_config,
)

LIU_YAO_CLI = ROOT / "build" / "examples" / "liu_yao_web_cli"
CONFIG = load_reading_config()


def yao(position, branch, element, relative, state):
    return {"position": position, "mainPillar": {"branch": branch},
            "mainElement": element, "mainRelative": relative, "wangShuai": state}


class LiuyaoDistributionTests(unittest.TestCase):
    def real_qian_chart(self):
        completed = subprocess.run(
            [str(LIU_YAO_CLI)], input=json.dumps(
                {"calendar": "solar", "date": {"year": 2025, "month": 2, "day": 12, "hour": 10},
                 "hexagram_code": "111111", "changing_lines": []}),
            capture_output=True, text=True, timeout=30, cwd=ROOT, check=False)
        self.assertEqual(completed.returncode, 0, completed.stdout[:200])
        return json.loads(completed.stdout)

    def test_real_kernel_chart_locked(self):
        if not LIU_YAO_CLI.exists():
            self.skipTest("liu_yao_web_cli 未构建")
        chart = self.real_qian_chart()
        # DEF-4 修复后月令表交叉锁：寅月乾宫 水休 木旺 土死 火相 金囚 土死
        self.assertEqual([y["wangShuai"] for y in sorted(chart["yao"], key=lambda x: x["position"])],
                         ["休", "旺", "死", "相", "囚", "死"])
        result = compute_liuyao_distribution(chart, CONFIG)
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["point_basis"]["count"], 6)
        charts = {c["id"]: c for c in result["charts"]}
        # 六亲：父母2(辰戌) 兄弟1 子孙1 妻财1 官鬼1 → 33/17/17/17/16，父母主导
        pct = lambda cid: {s["key"]: s["percent"] for s in charts[cid]["segments"]}
        self.assertEqual(pct("rels"), {"父母": 33, "兄弟": 17, "子孙": 17, "妻财": 17, "官鬼": 16})
        self.assertEqual(charts["rels"]["dominant"]["key"], "父母")
        # 五行：土2 其余各1 → 木17 火17 土33 金17 水16
        self.assertEqual(pct("signs"), {"木": 17, "火": 17, "土": 33, "金": 17, "水": 16})
        self.assertEqual(charts["signs"]["dominant"]["key"], "土")
        # 旺衰：死2 其余各1 → 旺17 相17 休17 囚16 死33
        self.assertEqual(pct("states"), {"旺": 17, "相": 17, "休": 17, "囚": 16, "死": 33})
        self.assertEqual(charts["states"]["dominant"]["key"], "死")
        for c in result["charts"]:
            self.assertEqual(sum(pct(c["id"]).values()), 100)
        self.assertEqual(result["summary_zh"], "此卦的底色：涵泳滋养×厚重承载×深藏伏机。")

    def test_synthetic_three_way_tie_balanced(self):
        chart = {"yao": [
            yao(1, "子", "水", "父母", "旺"), yao(2, "丑", "土", "父母", "旺"),
            yao(3, "寅", "木", "兄弟", "相"), yao(4, "卯", "木", "兄弟", "相"),
            yao(5, "辰", "土", "子孙", "休"), yao(6, "巳", "火", "子孙", "休"),
        ]}
        result = compute_liuyao_distribution(chart, CONFIG)
        charts = {c["id"]: c for c in result["charts"]}
        self.assertIsNone(charts["rels"]["dominant"], "三向平局应判 balanced")
        rels_phrase = charts["rels"]["headline_zh"]
        self.assertIn("五亲均匀", rels_phrase)
        # 五行 木2土2水1火1金0 → 平局 balanced；旺衰 旺2相2休2 → 平局
        self.assertEqual(charts["signs"]["dominant"], None)
        self.assertEqual(charts["states"]["dominant"], None)
        self.assertEqual(result["summary_zh"], "此卦的底色：五亲并济×五气匀停×五态参差。")

    def test_dirty_chart_rejected(self):
        with self.assertRaises(AstroDistributionRequestError):
            compute_liuyao_distribution({"yao": [yao(1, "子", "水", "父母", "旺")]}, CONFIG)
        unknown_state = {"yao": [yao(i, "子", "水", "父母", s if i != 3 else "未知")
                                 for i, s in enumerate(["旺", "相", "旺", "囚", "死", "休"], start=1)]}
        with self.assertRaises(AstroDistributionRequestError):
            compute_liuyao_distribution(unknown_state, CONFIG)
        bad_rel = {"yao": [yao(1, "子", "水", "游魂", "旺")] +
                   [yao(i, "丑", "土", "兄弟", "相") for i in range(2, 7)]}
        with self.assertRaises(AstroDistributionRequestError):
            compute_liuyao_distribution(bad_rel, CONFIG)

    def test_reading_texts_have_no_auspice_claims(self):
        banned = ("主吉", "主凶", "大吉", "必凶", "必胜", "必败", "断曰", "用神")
        for chart in CONFIG["charts"].values():
            blob = (chart["title_zh"] + chart["basis_zh"] + chart["balanced_template_zh"]
                    + "".join(chart["readings_zh"].values())
                    + "".join(chart["summary_phrases_zh"].values()))
            for word in banned:
                self.assertNotIn(word, blob, f"{chart['title_zh']} 含禁词 {word}")

    def test_route_wired_everywhere(self):
        manifest = json.loads((ROOT / "config/platform/tools/liu_yao.json").read_text(encoding="utf-8"))
        self.assertIn("/api/v1/liu-yao/distribution", {r["path"] for r in manifest["routes"]})
        server = (ROOT / "web" / "server.py").read_text(encoding="utf-8")
        self.assertIn('"/api/v1/liu-yao/distribution"', server)
        self.assertIn("def run_liuyao_distribution", server)
        page = (ROOT / "web" / "liu-yao.html").read_text(encoding="utf-8")
        self.assertIn('id="ly-profile-charts"', page)
        self.assertIn("/profile-charts.js", page)
        javascript = (ROOT / "web" / "liu-yao.js").read_text(encoding="utf-8")
        self.assertIn("/api/v1/liu-yao/distribution", javascript)


if __name__ == "__main__":
    unittest.main()
