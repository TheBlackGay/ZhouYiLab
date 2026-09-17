import json
import os
import subprocess
import unittest
from pathlib import Path

from web.astro_natal_analysis import (
    AstroNatalAnalysisRequestError,
    analyze_natal_layout,
    load_rules,
)
from web.astro_natal_reading import (
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
DETERMINISTIC_WORDS = ("一定会", "必然", "注定", "你就是", "你会")


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
        # N2 只交付布局速读，逐点位卡片留到 N3。
        self.assertEqual(reading["points"], [])
        self.assertEqual(reading["coverage"]["matched"], reading["coverage"]["rendered"])
        self.assertTrue(reading["boundaries"])

    def test_reading_wording_avoids_deterministic_claims(self):
        reading = render_natal_reading(analyze_natal_layout(self.chart()))
        texts = [entry["text"] for entry in reading["layout"]]
        texts += [item["summary"] for item in reading["highlights"].values()]
        texts += reading["boundaries"]
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