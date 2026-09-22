"""大六壬 2.0.0 页面契约（DLR-201/202/203/204 + 验收案例）。

静态断言（与 qimen/bazi 契约测试同风格）+ 一次真实起课数据形状校验。
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "web" / "da-liu-ren.html").read_text(encoding="utf-8")
JAVASCRIPT = (ROOT / "web" / "da-liu-ren.js").read_text(encoding="utf-8")
GLOSSARY = json.loads((ROOT / "config" / "daliuren" / "glossary.json").read_text(encoding="utf-8"))
DLR_CLI = ROOT / "build" / "examples" / "da_liu_ren_web_cli"

GLOSSARY_IDS = {term["id"] for term in GLOSSARY["terms"]}


class DaLiuRenInputTests(unittest.TestCase):
    """DLR-201 / DLR-202 输入与问题上下文。"""

    def test_question_types_match_spec(self):
        block = re.search(r'<select id="question-type">(.*?)</select>', HTML, re.DOTALL).group(1)
        options = set(re.findall(r'<option value="([^"]+)"', block))
        self.assertEqual({"general", "love", "career", "wealth", "travel", "health", "other"}, options)

    def test_leap_month_and_quick_actions_present(self):
        self.assertIn('id="leap-month"', HTML)
        self.assertIn('id="fill-now"', HTML)
        self.assertIn('id="fill-sample"', HTML)
        self.assertIn("夜子", JAVASCRIPT)          # 子时换日口径显式化
        self.assertIn("分钟不参与", HTML)

    def test_submit_disables_button_and_keeps_form_on_error(self):
        self.assertIn("button.disabled = true;", JAVASCRIPT)
        self.assertIn("button.disabled = false;", JAVASCRIPT)
        self.assertIn("error.hidden = false", JAVASCRIPT)  # 失败仅提示，输入不清空

    def test_question_notes_never_sent(self):
        # 请求体固定为 { calendar, date }；问题类型/描述只允许出现在页面渲染路径。
        self.assertIn("const request = { calendar, date };", JAVASCRIPT)
        self.assertNotIn("body: JSON.stringify({ calendar", JAVASCRIPT)
        self.assertNotIn("notes,", JAVASCRIPT.replace("// ", ""))


class DaLiuRenDualModeTests(unittest.TestCase):
    """DLR-203 双模式：同一份数据切换，不重复请求。"""

    def test_mode_toggle_and_shared_data(self):
        self.assertIn('name="result-mode"', HTML)
        self.assertIn('value="beginner"', HTML)
        self.assertIn('value="pro"', HTML)
        self.assertEqual(2, JAVASCRIPT.count("fetch("),
                         "仅允许 起课 与 术语库 两个 fetch；模式切换不得请求接口")

    def test_beginner_flow_stages(self):
        for label in ("起因", "发展", "归结"):
            self.assertIn(label, JAVASCRIPT)

    def test_beginner_makes_no_auspice_claims(self):
        self.assertIn("不提供吉凶断语", HTML)
        for banned in ("主大吉", "必凶", "定应"):
            self.assertNotIn(banned, HTML)
            self.assertNotIn(banned, JAVASCRIPT)

    def test_professional_panels_complete(self):
        for panel in ("sike-panel", "pan-panel", "extra-panel", "rule-panel"):
            self.assertIn(f'id="{panel}"', HTML)
        self.assertIn("pan-table", JAVASCRIPT)
        self.assertIn("rule_profile", JAVASCRIPT)   # 专业视图必须能展示口径


class DaLiuRenGlossaryAnchorsTests(unittest.TestCase):
    """DLR-204：页面术语锚点与术语库 id 交叉一致，且必须走清单声明的路由。"""

    def test_every_term_anchor_exists_in_glossary(self):
        anchors = set(re.findall(r'data-term="([a-z_]+)"', HTML))
        anchors |= {m.group(1) for m in re.finditer(r"termButton\('([a-z_]+)'\)", JAVASCRIPT)}
        for stage in ("chu_chuan", "zhong_chuan", "mo_chuan"):
            anchors.add(stage)  # 动态 termButton(item.stage)
        unknown = anchors - GLOSSARY_IDS
        self.assertEqual(unknown, set(), "页面引用了术语库中不存在的词条")

    def test_glossary_served_from_registry_route(self):
        self.assertIn("/api/v1/da-liu-ren/glossary", JAVASCRIPT)
        manifest = json.loads(
            (ROOT / "config" / "platform" / "tools" / "da_liu_ren.json").read_text(encoding="utf-8"))
        route = next(r for r in manifest["routes"] if r["path"] == "/api/v1/da-liu-ren/glossary")
        self.assertEqual(route["handler"], "static_config")

    def test_dialog_keyboard_and_mobile(self):
        self.assertIn("<dialog id=\"glossary-dialog\"", HTML)
        self.assertIn("glossary-close", JAVASCRIPT)


class DaLiuRenChartPayloadTests(unittest.TestCase):
    """验收案例 3/4 的数据面：天地盘 12 位、三传含遁干六亲、四柱无异常。"""

    @classmethod
    def setUpClass(cls):
        if not DLR_CLI.exists():
            raise unittest.SkipTest("da_liu_ren_web_cli 尚未构建")

    def test_chart_shape_for_acceptance(self):
        request = {"calendar": "solar", "date": {"year": 2025, "month": 11, "day": 3, "hour": 16}}
        completed = subprocess.run([str(DLR_CLI)], input=json.dumps(request),
                                   capture_output=True, text=True, timeout=30, check=False)
        data = json.loads(completed.stdout)
        pillars = [data["ba_zi"][k] for k in ("year", "month", "day", "hour")]
        for pillar in pillars:
            self.assertIsInstance(pillar, dict)
            self.assertTrue(pillar.get("stem") and pillar.get("branch"))
        self.assertEqual(len(data["tian_di_pan"]), 12)
        details = data["san_chuan"]["details"]
        self.assertEqual([x["stage"] for x in details], ["chu_chuan", "zhong_chuan", "mo_chuan"])
        for item in details:
            self.assertTrue(item["branch"] and item["liu_qin"])


if __name__ == "__main__":
    unittest.main()
