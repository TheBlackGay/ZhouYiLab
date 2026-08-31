import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "web"))

from ziwei_analysis import (  # noqa: E402
    AnalysisRequestError,
    analyze_natal_chart,
    load_analysis_resources,
)


PALACE_NAMES = [
    "疾厄宫", "财帛宫", "子女宫", "夫妻宫", "兄弟宫", "命宫",
    "父母宫", "福德宫", "田宅宫", "官禄宫", "奴仆宫", "迁移宫",
]
SHEN_SHA_VALUES = {
    "chang_sheng_12": ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养"],
    "bo_shi_12": ["博士", "力士", "青龙", "小耗", "将军", "奏书", "飞廉", "喜神", "病符", "大耗", "伏兵", "官府"],
    "sui_qian_12": ["岁建", "晦气", "丧门", "贯索", "官符", "小耗", "大耗", "龙德", "白虎", "天德", "吊客", "病符"],
    "jiang_qian_12": ["将星", "攀鞍", "岁驿", "息神", "华盖", "劫煞", "灾煞", "天煞", "指背", "咸池", "月煞", "亡神"],
}


def make_chart():
    palaces = []
    for index, name in enumerate(PALACE_NAMES):
        palaces.append({
            "name": name,
            "gan_zhi": f"测试{index}",
            "is_ming_palace": name == "命宫",
            "is_body_palace": False,
            "zhu_xing": [],
            "fu_xing_detail": [],
            "sha_xing_detail": [],
            "za_yao_detail": [],
            "shen_sha": {system: values[index] for system, values in SHEN_SHA_VALUES.items()},
        })
    palaces[5]["zhu_xing"] = [
        {"name": "紫微", "liang_du": "庙"},
        {"name": "破军", "liang_du": "旺", "si_hua": "化权"},
    ]
    palaces[6]["sha_xing_detail"] = [{"name": "铃星", "liang_du": "平"}]
    palaces[0]["zhu_xing"] = [{"name": "天同", "liang_du": "利"}]
    palaces[10]["zhu_xing"] = [{"name": "巨门", "liang_du": "旺"}]
    return {"palaces": palaces, "ming_gong_index": 5, "shen_gong_index": 5}


class ZiWeiAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.symbolism, cls.cases, cls.shen_sha, cls.patterns = load_analysis_resources()

    def analyze(self, chart=None, scope=None):
        return analyze_natal_chart(
            chart or make_chart(),
            scope,
            symbolism=self.symbolism,
            cases=self.cases,
            shen_sha=self.shen_sha,
            patterns=self.patterns,
        )

    def test_all_twelve_palaces_are_analyzed_by_default(self):
        result = self.analyze()
        self.assertEqual(12, len(result["palaces"]))
        self.assertEqual(set(PALACE_NAMES), {item["palace"] for item in result["palaces"]})
        self.assertEqual("all_candidates", result["scope"]["scenario_mode"])

    def test_parents_palace_keeps_original_and_career_derivation(self):
        result = self.analyze(scope={
            "layers": ["natal"],
            "focus_palaces": ["父母宫"],
            "scenarios": ["职场"],
        })
        palace_fragment = result["fragments"][0]
        original_ids = {item["id"] for item in palace_fragment["original_meanings"]}
        derived_ids = {item["id"] for item in palace_fragment["derived_meanings"]}
        self.assertIn("parents.direct_authority", original_ids)
        self.assertEqual({"parents.manager"}, derived_ids)
        self.assertEqual("父母宫", palace_fragment["effect_palace"])

    def test_star_fragment_preserves_physical_palace_and_relation(self):
        result = self.analyze(scope={"focus_palaces": ["父母宫"]})
        lingxing = next(
            fragment for fragment in result["fragments"]
            if fragment["type"] == "star_in_palace"
            and fragment["facts"]["star"] == "铃星"
        )
        self.assertEqual("父母宫", lingxing["facts"]["physical_palace"])
        self.assertEqual("self", lingxing["facts"]["relation"])
        self.assertEqual("父母宫", lingxing["effect_palace"])

    def test_four_directions_use_physical_positions(self):
        result = self.analyze(scope={"focus_palaces": ["父母宫"]})
        palace = result["palaces"][0]
        self.assertEqual(["奴仆宫", "子女宫"], [
            item["palace"] for item in palace["four_directions"]["triads"]
        ])
        self.assertEqual("疾厄宫", palace["four_directions"]["opposite"]["palace"])
        tian_tong = next(
            fragment for fragment in result["fragments"]
            if fragment["type"] == "four_directions"
            and fragment["facts"]["star"] == "天同"
        )
        self.assertEqual("opposite", tian_tong["facts"]["relation"])
        self.assertEqual("疾厄宫", tian_tong["facts"]["physical_palace"])

    def test_empty_palace_borrows_only_when_opposite_has_primary_star(self):
        chart = make_chart()
        result = self.analyze(chart, {"focus_palaces": ["父母宫"]})
        rule_ids = {
            fragment.get("facts", {}).get("rule_id") for fragment in result["fragments"]
        }
        self.assertIn("palace.empty.borrow_opposite", rule_ids)

        chart["palaces"][0]["zhu_xing"] = []
        result = self.analyze(chart, {"focus_palaces": ["父母宫"]})
        rule_ids = {
            fragment.get("facts", {}).get("rule_id") for fragment in result["fragments"]
        }
        self.assertNotIn("palace.empty.borrow_opposite", rule_ids)

    def test_same_palace_combination_is_loaded_from_static_rule(self):
        result = self.analyze(scope={"focus_palaces": ["命宫"]})
        combination = next(
            fragment for fragment in result["fragments"]
            if fragment.get("facts", {}).get("rule_id")
            == "combination.ziwei.pojun.same_palace"
        )
        self.assertEqual("combination", combination["type"])
        self.assertEqual("命宫", combination["effect_palace"])
        palace = result["palaces"][0]
        self.assertIn(combination["fragment_id"], palace["sections"]["combinations"])
        self.assertNotIn(combination["fragment_id"], palace["sections"]["patterns"])

    def test_pattern_comes_from_authoritative_catalog_without_legacy_duplicate(self):
        chart = make_chart()
        chart["palaces"][5]["zhu_xing"] = [
            {"name": "紫微", "liang_du": "庙"},
            {"name": "天府", "liang_du": "旺"},
        ]
        result = self.analyze(chart, {"focus_palaces": ["命宫"]})
        patterns = [
            fragment for fragment in result["fragments"]
            if fragment.get("facts", {}).get("rule_id") == "pattern.zifu.same_palace"
        ]
        self.assertEqual(1, len(patterns))
        self.assertEqual("pattern_catalog", patterns[0]["evidence"][0]["source"])
        self.assertIn(patterns[0]["fragment_id"], result["palaces"][0]["sections"]["patterns"])

    def test_pattern_engine_marks_legacy_cpp_results_non_authoritative(self):
        chart = make_chart()
        chart["ge_ju"] = ["旧格局结果"]
        result = self.analyze(chart, {"focus_palaces": ["命宫"]})
        self.assertTrue(result["pattern_engine"]["authoritative_for_structured_analysis"])
        self.assertTrue(result["pattern_engine"]["legacy_cpp_ge_ju"]["present"])
        self.assertFalse(
            result["pattern_engine"]["legacy_cpp_ge_ju"]
            ["authoritative_for_structured_analysis"]
        )

    def test_sanqi_pattern_effect_belongs_to_parent_palace(self):
        chart = make_chart()
        chart["palaces"][6]["zhu_xing"] = [
            {"name": "廉贞", "si_hua": "化禄"},
        ]
        chart["palaces"][2]["zhu_xing"] = [
            {"name": "破军", "si_hua": "化权"},
        ]
        chart["palaces"][10]["zhu_xing"] = [
            {"name": "武曲", "si_hua": "化科"},
        ]
        result = self.analyze(chart, {"focus_palaces": ["父母宫"]})
        pattern = next(
            fragment for fragment in result["fragments"]
            if fragment.get("facts", {}).get("rule_id")
            == "pattern.sanqi.four_directions"
        )
        self.assertEqual("父母宫", pattern["effect_palace"])
        self.assertIn("直接权威", pattern["effect_subject"])
        self.assertTrue(pattern["condition_trace"]["required"]["matched"])

    def test_non_natal_layer_is_rejected(self):
        with self.assertRaisesRegex(AnalysisRequestError, "仅支持 natal"):
            self.analyze(scope={"layers": ["annual"]})

    def test_duplicate_focus_palace_is_rejected(self):
        with self.assertRaisesRegex(AnalysisRequestError, "重复宫位"):
            self.analyze(scope={"focus_palaces": ["父母宫", "父母宫"]})

    def test_explicit_empty_scenarios_is_rejected(self):
        with self.assertRaisesRegex(AnalysisRequestError, "非空字符串数组"):
            self.analyze(scope={"scenarios": []})

    def test_sections_group_self_triad_and_opposite_stars(self):
        result = self.analyze(scope={"focus_palaces": ["父母宫"]})
        palace = result["palaces"][0]
        fragments = {item["fragment_id"]: item for item in palace["fragments"]}
        self.assertTrue(all(
            fragments[item]["facts"]["relation"] == "self"
            for item in palace["sections"]["self_stars"]
        ))
        self.assertTrue(all(
            fragments[item]["facts"]["relation"] == "triad"
            for item in palace["sections"]["triad_stars"]
        ))
        self.assertTrue(all(
            fragments[item]["facts"]["relation"] == "opposite"
            for item in palace["sections"]["opposite_stars"]
        ))

    def test_transformation_is_not_duplicated_in_star_modifiers(self):
        result = self.analyze(scope={"focus_palaces": ["命宫"]})
        star = next(item for item in result["fragments"] if item.get("facts", {}).get("star") == "破军" and item["type"] == "star_in_palace")
        transformation = next(item for item in result["fragments"] if item["type"] == "transformation")
        self.assertNotIn("transformation", {item["type"] for item in star["modifiers"]})
        self.assertEqual([transformation["fragment_id"]], star["related_fragment_ids"])

    def test_focus_palace_has_four_distinct_shen_sha_fragments(self):
        chart = make_chart()
        chart["palaces"][5]["shen_sha"].update({"bo_shi_12": "大耗", "sui_qian_12": "大耗"})
        result = self.analyze(chart, {"focus_palaces": ["命宫"]})
        fragments = [item for item in result["fragments"] if item["type"] == "shen_sha_in_palace"]
        self.assertEqual(4, len(fragments))
        same_name = [item for item in fragments if item["facts"]["shen_sha"] == "大耗"]
        self.assertEqual({"bo_shi_12", "sui_qian_12"}, {item["facts"]["system"] for item in same_name})
        self.assertEqual(2, len({item["fragment_id"] for item in same_name}))

    def test_common_misc_star_enters_configured_reasoning(self):
        chart = make_chart()
        chart["palaces"][5]["za_yao_detail"] = [{"name": "天喜", "liang_du": "旺"}]
        result = self.analyze(chart, {"focus_palaces": ["命宫"]})
        palace = result["palaces"][0]
        tianxi = next(item for item in palace["fragments"] if item.get("facts", {}).get("star") == "天喜")
        self.assertEqual("miscellaneous", tianxi["facts"]["star_category"])
        self.assertNotIn("天喜", {item["name"] for item in palace["facts"]["unconfigured_stars"]})

    def test_ai_packet_references_valid_fragments_and_classifies_signals(self):
        result = self.analyze(scope={"focus_palaces": ["命宫"]})
        valid_ids = {item["fragment_id"] for item in result["fragments"]}
        packet = result["ai_packet"]["palaces"][0]
        referenced = set(packet["core_signal_ids"] + packet["supporting_signal_ids"] + packet["tension_signal_ids"] + packet["evidence_fragment_ids"])
        self.assertTrue(referenced <= valid_ids)
        self.assertTrue(packet["core_signal_ids"])
        self.assertTrue(packet["supporting_signal_ids"])

    def test_backward_compatible_flat_fragments_remain_available(self):
        result = self.analyze(scope={"focus_palaces": ["命宫"]})
        self.assertEqual(result["palaces"][0]["fragments"], result["fragments"])


if __name__ == "__main__":
    unittest.main()
