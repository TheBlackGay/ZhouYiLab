import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from web.astro_natal_analysis import (
    POINT_ORDER,
    AstroNatalAnalysisRequestError,
    analyze_natal_layout,
    load_rules,
)
from web.astro_natal_reading import (
    AstroNatalReadingConfigError,
    AstroNatalReadingRequestError,
    load_templates,
    render_natal_reading,
)


ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "build" / "examples" / "astro_web_cli"
DISTRIBUTION_POINT_IDS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
]
DETERMINISTIC_WORDS = ("一定会", "必然", "注定", "你就是", "你会", "必定", "绝对", "永远", "肯定会")


def run_cli(request):
    env = os.environ.copy()
    env["ZHOUYILAB_EPHEMERIS_PATH"] = str(ROOT / "data" / "ephemeris")
    completed = subprocess.run(
        [str(CLI)], input=json.dumps(request), text=True,
        capture_output=True, env=env, cwd=ROOT, check=True,
    )
    return json.loads(completed.stdout)


@unittest.skipUnless(CLI.exists(), "astro_web_cli has not been built")
class AstroNatalAnalysisTests(unittest.TestCase):
    """1990-05-20 上海 14:00 的固定盘，作为布局统计的回归基线。"""

    def chart(self):
        return run_cli({
            "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
            "utc_offset_minutes": 480,
            "location": {"latitude": 31.2304, "longitude": 121.4737},
            "include_aspects": True,
        })

    def test_layout_statistics_match_hand_counted_baseline(self):
        packet = analyze_natal_layout(self.chart())
        self.assertEqual(packet["analysis_version"], "astro-natal-analysis/1.0")
        self.assertEqual(packet["rules_version"], "astro-natal-rules/1.0")
        self.assertEqual(packet["ruler_system"], "modern")
        self.assertEqual(packet["source_schema_versions"]["structured"], "astro-structured/1.0")

        layout = packet["layout"]
        hemispheres = {item["name"]: item for item in layout["hemispheres"]["items"]}
        # 半球、象限只统计十大行星，且左+右、上+下必须等于统计总数。
        self.assertEqual(layout["hemispheres"]["counted_point_ids"], DISTRIBUTION_POINT_IDS)
        self.assertEqual(layout["hemispheres"]["counted_total"], 10)
        self.assertEqual(hemispheres["left"]["count"], 2)
        self.assertEqual(hemispheres["right"]["count"], 8)
        self.assertEqual(hemispheres["left"]["count"] + hemispheres["right"]["count"], 10)
        self.assertEqual(hemispheres["above"]["count"], 5)
        self.assertEqual(hemispheres["below"]["count"], 5)
        self.assertEqual(hemispheres["left"]["point_ids"], ["jupiter", "pluto"])
        self.assertEqual(hemispheres["right"]["point_ids"],
                         ["sun", "moon", "mercury", "venus", "mars", "saturn", "uranus", "neptune"])
        self.assertEqual(hemispheres["left"]["ratio"], 0.2)
        self.assertEqual(hemispheres["right"]["ratio"], 0.8)

        quadrants = {item["name"]: item["count"] for item in layout["quadrants"]["items"]}
        self.assertEqual(quadrants, {"1": 1, "2": 4, "3": 4, "4": 1})
        self.assertEqual(sum(quadrants.values()), 10)

        self.assertEqual(layout["house_occupancy"]["empty_houses"], [1, 3, 5, 11, 12])
        sign_counts = {item["sign_id"]: item["count"] for item in layout["sign_occupancy"]["items"]}
        self.assertEqual(len(sign_counts), 12)
        self.assertEqual(sign_counts["capricorn"], 3)
        self.assertEqual(sign_counts["taurus"], 2)
        self.assertEqual(sign_counts["pisces"], 2)
        self.assertEqual(sum(sign_counts.values()), 10)
        # 12 个星座名必须齐全，即使 chart 的宫头没有落在该座。
        self.assertEqual(all(item["sign_name"] and item["sign_name"] != item["sign_id"]
                             for item in layout["sign_occupancy"]["items"]), True)

        self.assertEqual(layout["elements"], {"fire": 1, "earth": 5, "air": 1, "water": 5})
        self.assertEqual(layout["modalities"], {"cardinal": 6, "fixed": 4, "mutable": 2})

        network = layout["aspect_network"]
        self.assertEqual(network["total"], 29)
        self.assertEqual(network["by_type"],
                         {"conjunction": 3, "sextile": 9, "square": 6,
                          "trine": 6, "opposition": 5, "quincunx": 0})
        self.assertEqual(network["harmony"], 15)
        self.assertEqual(network["tension"], 11)
        self.assertEqual(network["neutral"], 3)
        self.assertEqual(network["dominant"], "harmony")
        self.assertEqual(network["tight"], 8)
        self.assertEqual(network["mean_orb"], 4.4578)

    def test_core_points_and_chart_ruler_are_resolved(self):
        layout = analyze_natal_layout(self.chart())["layout"]
        self.assertEqual(layout["core"]["ascendant"]["sign_id"], "virgo")
        self.assertEqual(layout["core"]["ascendant"]["sign_name"], "处女座")
        self.assertEqual(layout["core"]["sun"]["sign_id"], "taurus")
        self.assertEqual(layout["core"]["sun"]["house"], 9)
        self.assertEqual(layout["core"]["moon"]["sign_id"], "pisces")
        self.assertEqual(layout["core"]["moon"]["house"], 7)
        self.assertEqual(layout["core"]["chart_ruler"]["point_id"], "mercury")
        self.assertEqual(layout["core"]["chart_ruler"]["house"], 8)

    def test_ruler_system_switch_changes_house_rulers(self):
        chart = self.chart()
        modern = {fact["signal_id"]: fact for fact in analyze_natal_layout(chart)["facts"]}
        traditional = {fact["signal_id"]: fact for fact in
                       analyze_natal_layout(chart, "traditional")["facts"]}
        # 天蝎（第3宫宫头）现代主星为冥王，传统主星为火星。
        self.assertEqual(modern["house_ruler_placement:3"]["evidence"]["ruler_id"], "pluto")
        self.assertEqual(traditional["house_ruler_placement:3"]["evidence"]["ruler_id"], "mars")
        # 水瓶（第5宫宫头）现代主星为天王，传统主星为土星。
        self.assertEqual(modern["house_ruler_placement:5"]["evidence"]["ruler_id"], "uranus")
        self.assertEqual(traditional["house_ruler_placement:5"]["evidence"]["ruler_id"], "saturn")

    def test_every_fact_carries_evidence_and_point_names(self):
        packet = analyze_natal_layout(self.chart())
        self.assertTrue(packet["facts"])
        for fact in packet["facts"]:
            self.assertTrue(fact["signal_id"])
            self.assertTrue(fact["type"])
            self.assertIsInstance(fact["evidence"], dict)
            self.assertEqual(len(fact["point_ids"]), len(fact["point_names"]))
        # 命中规则的信号必须能回溯到规则版本与边界说明。
        self.assertTrue(packet["signals"])
        for signal in packet["signals"]:
            self.assertTrue(signal["rule_id"])
            self.assertGreaterEqual(signal["revision"], 1)
            self.assertTrue(signal["boundary"])
            self.assertTrue(signal["observation_code"])
        # 未命中规则的信号必须显式列出，不能静默丢弃。
        matched = {signal["signal_id"] for signal in packet["signals"]}
        facts = {fact["signal_id"] for fact in packet["facts"]}
        self.assertEqual(matched | {item["signal_id"] for item in packet["uncovered"]}, facts)

    def test_layout_statistics_do_not_depend_on_rules(self):
        chart = self.chart()
        without_rules = analyze_natal_layout(chart, rules={"schema_version": "astro-natal-rules/1.0", "rules": []})
        with_rules = analyze_natal_layout(chart)
        self.assertEqual(without_rules["layout"], with_rules["layout"])
        self.assertEqual(without_rules["signals"], [])
        self.assertEqual(len(without_rules["uncovered"]), len(without_rules["facts"]))

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(AstroNatalAnalysisRequestError):
            analyze_natal_layout({"chart_type": "transit", "structured": {}})
        with self.assertRaises(AstroNatalAnalysisRequestError):
            analyze_natal_layout(self.chart(), "vedic")
        with self.assertRaises(AstroNatalAnalysisRequestError):
            analyze_natal_layout({"chart_type": "natal"})

    def test_rules_are_configured_and_validated(self):
        rules = load_rules()
        self.assertEqual(rules["schema_version"], "astro-natal-rules/1.0")
        self.assertGreaterEqual(len(rules["rules"]), 12)
        rule_ids = [rule["rule_id"] for rule in rules["rules"]]
        self.assertEqual(len(rule_ids), len(set(rule_ids)))
        for rule in rules["rules"]:
            self.assertTrue(rule["boundary"])


@unittest.skipUnless(CLI.exists(), "astro_web_cli has not been built")
class AstroNatalReadingTests(unittest.TestCase):
    def chart(self):
        return run_cli({
            "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
            "utc_offset_minutes": 480,
            "location": {"latitude": 31.2304, "longitude": 121.4737},
            "include_aspects": True,
        })

    def test_reading_renders_layout_lines_without_placeholders(self):
        reading = render_natal_reading(analyze_natal_layout(self.chart()))
        self.assertEqual(reading["reading_version"], "astro-natal-reading/1.0")
        self.assertEqual(reading["templates_version"], "astro-natal-templates/1.0")
        self.assertEqual(reading["ruler_system"], "modern")
        self.assertEqual(set(reading["highlights"]), {"ascendant", "sun", "moon", "chart_ruler"})
        for slot, item in reading["highlights"].items():
            self.assertTrue(item["title"], slot)
            self.assertTrue(item["summary"], slot)
        self.assertTrue(reading["layout"])
        for entry in reading["layout"]:
            self.assertNotIn("{", entry["text"])
            self.assertNotIn("—", entry["text"])
            self.assertTrue(entry["rule_id"])
            self.assertGreaterEqual(entry["revision"], 1)
            self.assertTrue(entry["signal_ids"])
        # N3 起逐点位、十二宫与相位卡片都由组合式文案填充。
        self.assertEqual(len(reading["points"]), 12)
        self.assertEqual(len(reading["houses"]), 12)
        self.assertEqual(len(reading["aspects"]), 29)
        self.assertEqual(reading["coverage"]["matched"], reading["coverage"]["rendered"])
        self.assertTrue(reading["boundaries"])

    def test_reading_wording_avoids_deterministic_claims(self):
        reading = render_natal_reading(analyze_natal_layout(self.chart()))
        texts = [entry["text"] for entry in reading["layout"]]
        texts += [item["summary"] for item in reading["highlights"].values()]
        texts += [item["fact"] for item in reading["highlights"].values()]
        texts += [point["summary"] for point in reading["points"]]
        texts += [block["text"] for point in reading["points"] for block in point["blocks"]]
        texts += [house["summary"] for house in reading["houses"]]
        texts += [block["text"] for house in reading["houses"] for block in house["blocks"]]
        texts += [aspect["summary"] for aspect in reading["aspects"]]
        texts += reading["boundaries"]
        self.assertGreater(len(texts), 120)
        for text in texts:
            for word in DETERMINISTIC_WORDS:
                self.assertNotIn(word, text)

    def test_reading_accepts_analysis_without_chart(self):
        analysis = analyze_natal_layout(self.chart())
        from_chart = render_natal_reading(analysis)
        from_analysis = render_natal_reading(json.loads(json.dumps(analysis)))
        self.assertEqual(from_chart["layout"], from_analysis["layout"])
        self.assertEqual(from_chart["highlights"], from_analysis["highlights"])
        # 点位中文名在事实层解析，解读层不需要 chart 也能渲染。
        self.assertTrue(any("星" in item["summary"] for item in from_analysis["highlights"].values()))

    def test_reading_requires_natal_analysis_packet(self):
        with self.assertRaises(AstroNatalReadingRequestError):
            render_natal_reading({"analysis_version": "astro-analysis/1.0", "signals": []})
        with self.assertRaises(AstroNatalReadingRequestError):
            render_natal_reading({"analysis_version": "astro-natal-analysis/1.0"})

    def test_point_cards_are_composed_from_three_slots(self):
        reading = render_natal_reading(analyze_natal_layout(self.chart()))
        points = {point["point_id"]: point for point in reading["points"]}
        self.assertEqual(set(points), set(POINT_ORDER))
        sun = points["sun"]
        self.assertEqual([block["slot"] for block in sun["blocks"]],
                         ["planet_core", "sign_style", "house_field"])
        self.assertEqual([block["rule_id"] for block in sun["blocks"]],
                         ["template.planet_core.sun", "template.sign_style.taurus",
                          "template.house_field.9"])
        self.assertEqual(sun["title"], "太阳 · 金牛座 · 第9宫")
        self.assertEqual(sun["summary"], "太阳落在金牛座第9宫：稳定、重实际，重心放在远方与高等学习。")
        # 每段文案都带中文标签，页面标题行与展开区直接复用。
        self.assertEqual([block["label"] for block in sun["blocks"]],
                         ["核心意志", "金牛座", "第9宫"])
        self.assertEqual(sun["evidence"]["house"], 9)
        self.assertIn("tight_aspect:sun:moon:sextile", sun["markers"])
        # 组合式渲染：同一星座/宫位文案被复用，但卡片主语只出现一次。
        self.assertEqual(points["moon"]["blocks"][1]["rule_id"], "template.sign_style.pisces")
        for point in reading["points"]:
            self.assertTrue(point["blocks"])
            self.assertEqual(point["blocks"][0]["slot"], "planet_core")
            self.assertTrue(all(block["revision"] >= 1 for block in point["blocks"]))

    def test_house_cards_carry_ruler_and_point_census(self):
        reading = render_natal_reading(analyze_natal_layout(self.chart()))
        houses = {house["house"]: house for house in reading["houses"]}
        self.assertEqual(len(houses), 12)
        self.assertEqual(houses[4]["title"], "第4宫 · 射手座")
        self.assertEqual(houses[4]["summary"], "第4宫宫头在射手座，宫内有土星、天王星、海王星。")
        self.assertEqual(houses[4]["ruler"]["point_id"], "jupiter")
        self.assertEqual(houses[4]["ruler"]["house"], 10)
        # 只统计十大行星时第5宫是空宫，但宫内确有虚点，文案必须说清楚。
        self.assertTrue(houses[5]["empty_of_planets"])
        self.assertEqual(houses[5]["point_ids"], ["true_node"])
        self.assertEqual(houses[5]["summary"],
                         "第5宫宫头在水瓶座，没有十大行星落入，宫内另有北交点。")
        # 十大行星与虚点同宫时两类都要出现。
        self.assertEqual(houses[10]["point_ids"], ["jupiter", "chiron"])
        self.assertIn("另有凯龙星", houses[10]["summary"])
        # 宫位卡片要能直接渲染点位名，并标出其中哪些是虚点。
        self.assertEqual(houses[10]["points"], [
            {"point_id": "jupiter", "point_name": "木星", "virtual": False},
            {"point_id": "chiron", "point_name": "凯龙星", "virtual": True},
        ])
        self.assertEqual(houses[5]["points"],
                         [{"point_id": "true_node", "point_name": "北交点", "virtual": True}])
        self.assertEqual([block["slot"] for block in houses[1]["blocks"]],
                         ["house_field", "house_ruler"])
        self.assertIn("主星水星落在金牛座第8宫", houses[1]["blocks"][1]["text"])
        self.assertEqual(reading["layout_stats"]["house_occupancy"]["empty_houses"],
                         [houses[house]["house"] for house in (1, 3, 5, 11, 12)])

    def test_aspect_cards_sort_by_orb_and_avoid_good_bad_labels(self):
        reading = render_natal_reading(analyze_natal_layout(self.chart()))
        orbs = [aspect["evidence"]["orb"] for aspect in reading["aspects"]]
        self.assertEqual(orbs, sorted(orbs))
        by_tone = {}
        for aspect in reading["aspects"]:
            by_tone.setdefault(aspect["tone"], []).append(aspect)
            self.assertIn(aspect["phase_label"], ("入相", "出相"))
            self.assertIn(aspect["label"], ("合相", "六合", "刑相", "拱相", "对冲", "梅花"))
            self.assertNotIn("吉", aspect["text"] if "text" in aspect else "")
            self.assertNotIn("凶", aspect["summary"])
        self.assertEqual(len(by_tone["harmony"]), 15)
        self.assertEqual(len(by_tone["tension"]), 11)
        self.assertEqual(len(by_tone["merge"]), 3)
        tight = [aspect for aspect in reading["aspects"] if aspect["tight"]]
        self.assertEqual(len(tight), 8)
        self.assertTrue(all(aspect["signal_ids"] for aspect in tight))
        self.assertEqual(reading["aspects"][0]["title"], "海王星 对冲 凯龙星")
        self.assertEqual(reading["aspects"][0]["orb"], 0.6756)

    def test_reading_has_no_placeholder_residue(self):
        reading = render_natal_reading(analyze_natal_layout(self.chart()))
        residue = []

        def walk(node, path):
            if isinstance(node, dict):
                for key, value in node.items():
                    walk(value, f"{path}.{key}")
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, f"{path}[{index}]")
            elif isinstance(node, str) and re.search(r"\{\w+\}|—", node):
                residue.append((path, node))

        walk(reading, "reading")
        self.assertEqual(residue, [])

    def test_overrides_replace_combination_slots(self):
        templates = json.loads(json.dumps(load_templates()))
        templates["overrides"]["point_sign"]["sun:taurus"] = {
            "revision": 7, "short": "精修过的金牛表达", "text": "太阳在金牛座的精修段落。"}
        templates["overrides"]["point_house"]["moon:7"] = {
            "revision": 8, "text": "月亮落第7宫的精修段落。"}
        templates["overrides"]["point_sign_house"]["mars:pisces:6"] = {
            "revision": 9, "short": "整段精修", "text": "火星双鱼第6宫的整段精修。"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "templates.json"
            path.write_text(json.dumps(templates, ensure_ascii=False), encoding="utf-8")
            validated = load_templates(path)
        reading = render_natal_reading(analyze_natal_layout(self.chart()), templates=validated)
        points = {point["point_id"]: point for point in reading["points"]}
        # 精修只替换对应槽位，其余组合段落保持模板输出。
        self.assertEqual([block["slot"] for block in points["sun"]["blocks"]],
                         ["planet_core", "point_sign", "house_field"])
        self.assertEqual(points["sun"]["blocks"][1]["text"], "太阳在金牛座的精修段落。")
        self.assertEqual(points["sun"]["blocks"][2]["rule_id"], "template.house_field.9")
        self.assertEqual(points["sun"]["overrides"], ["point_sign"])
        self.assertIn("精修过的金牛表达", points["sun"]["summary"])
        self.assertEqual([block["slot"] for block in points["moon"]["blocks"]],
                         ["planet_core", "sign_style", "point_house"])
        self.assertEqual(points["moon"]["overrides"], ["point_house"])
        # 整段精修替换星座与宫位两段，只保留星体基义。
        self.assertEqual([block["slot"] for block in points["mars"]["blocks"]],
                         ["planet_core", "point_sign_house"])
        self.assertEqual(points["mars"]["overrides"], ["point_sign_house"])
        self.assertIn("整段精修", points["mars"]["summary"])
        # 未精修的点位不受影响。
        self.assertEqual([block["slot"] for block in points["venus"]["blocks"]],
                         ["planet_core", "sign_style", "house_field"])

    def test_incomplete_templates_are_rejected(self):
        templates = json.loads(json.dumps(load_templates()))
        del templates["planet_core"]["chiron"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "templates.json"
            path.write_text(json.dumps(templates, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(AstroNatalReadingConfigError):
                load_templates(path)
        templates = json.loads(json.dumps(load_templates()))
        templates["layout_text"]["natal.empty_house"]["text"] = "第 {house} 宫，{unknown_key}。"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "templates.json"
            path.write_text(json.dumps(templates, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(AstroNatalReadingConfigError):
                load_templates(path)

    def test_every_configured_rule_has_a_template(self):
        rule_ids = {rule["rule_id"] for rule in load_rules()["rules"]}
        templates = load_templates()
        self.assertEqual(rule_ids - set(templates["layout_text"]), set())
        self.assertEqual(set(templates["core_text"]),
                         {"ascendant", "sun", "moon", "chart_ruler"})

    def test_reading_without_templates_reports_uncovered(self):
        templates = load_templates()
        templates = {**templates, "layout_text": {}}
        reading = render_natal_reading(analyze_natal_layout(self.chart()), templates=templates)
        self.assertEqual(reading["layout"], [])
        self.assertTrue(all(item["reason"] in {"no_rule", "no_template"} for item in reading["uncovered"]))
        self.assertTrue(any(item["reason"] == "no_template" for item in reading["uncovered"]))


if __name__ == "__main__":
    unittest.main()