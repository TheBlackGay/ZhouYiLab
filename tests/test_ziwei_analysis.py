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

    def test_ling_tan_external_auspicious_input_controls_grade(self):
        chart = make_chart()
        chart["si_zhu"] = {"year": "戊午"}
        ming_index = chart["ming_gong_index"]
        chart["palaces"][ming_index]["gan_zhi"] = "甲辰"
        chart["palaces"][ming_index]["zhu_xing"] = [{"name": "贪狼", "liang_du": "庙"}]
        chart["palaces"][ming_index]["sha_xing_detail"] = [{"name": "铃星", "liang_du": "庙"}]
        result = self.analyze(chart, {
            "focus_palaces": ["命宫"],
            "pattern_inputs": {"pattern.ling_tan_ge": {"has_auspicious": True}},
        })
        fragment = next(
            item for item in result["fragments"]
            if item.get("type") == "pattern"
            and item.get("facts", {}).get("rule_id") == "pattern.ling_tan_ge"
        )
        self.assertEqual("佳", fragment["facts"]["grade"])
        self.assertEqual(
            {"has_auspicious": True, "wu_ji_bonus": True},
            fragment["facts"]["flags"],
        )
        self.assertEqual(
            {"pattern.ling_tan_ge": {"has_auspicious": True}},
            result["scope"]["pattern_inputs"],
        )

    def test_pattern_inputs_reject_unknown_patterns_and_non_boolean_values(self):
        with self.assertRaisesRegex(AnalysisRequestError, "未知格局"):
            self.analyze(scope={"pattern_inputs": {"pattern.unknown": {"flag": True}}})
        with self.assertRaisesRegex(AnalysisRequestError, "布尔标记对象"):
            self.analyze(scope={
                "pattern_inputs": {
                    "pattern.ling_tan_ge": {"has_auspicious": "true"}
                }
            })

    def test_huo_tan_break_check_reaches_analysis_output(self):
        chart = make_chart()
        ming_index = chart["ming_gong_index"]
        chart["palaces"][ming_index]["gan_zhi"] = "甲未"
        chart["palaces"][ming_index]["zhu_xing"] = [{"name": "贪狼"}]
        chart["palaces"][ming_index]["sha_xing_detail"] = [
            {"name": "火星"}, {"name": "地空"},
        ]
        result = self.analyze(chart, {"focus_palaces": ["命宫"]})
        fragment = next(
            item for item in result["fragments"]
            if item.get("type") == "pattern"
            and item.get("facts", {}).get("rule_id") == "pattern.huo_tan_ge"
        )
        self.assertEqual("formed", fragment["facts"]["base_status"])
        self.assertEqual("broken", fragment["facts"]["status"])
        self.assertEqual("上格", fragment["facts"]["grade"])
        self.assertEqual(
            [{"star": "地空", "palace": "命宫", "branch": "未"}],
            fragment["facts"]["break_check"]["break_star_list"],
        )

    def test_zi_fu_chao_yuan_positions_grade_and_huaji_reach_analysis_output(self):
        chart = make_chart()
        ming_index = chart["ming_gong_index"]
        chart["palaces"][ming_index]["gan_zhi"] = "甲寅"
        chart["palaces"][ming_index]["zhu_xing"] = [{"name": "七杀"}]
        wu_index = (ming_index + 4) % 12
        xu_index = (ming_index + 8) % 12
        chart["palaces"][wu_index]["gan_zhi"] = "丙午"
        chart["palaces"][wu_index]["zhu_xing"] = [{"name": "天府"}]
        chart["palaces"][xu_index]["gan_zhi"] = "戊戌"
        chart["palaces"][xu_index]["zhu_xing"] = [
            {"name": "紫微", "si_hua": "化忌"}
        ]
        result = self.analyze(chart, {
            "focus_palaces": ["命宫"],
            "pattern_inputs": {
                "pattern.zi_fu_chao_yuan_ge": {"has_liu_lu": True}
            },
        })
        fragment = next(
            item for item in result["fragments"]
            if item.get("type") == "pattern"
            and item.get("facts", {}).get("rule_id") == "pattern.zi_fu_chao_yuan_ge"
        )
        self.assertEqual("broken", fragment["facts"]["status"])
        self.assertEqual("上格", fragment["facts"]["grade"])
        self.assertEqual(
            {"zi_palace": "戌", "fu_palace": "午"},
            fragment["facts"]["named_star_positions"],
        )
        self.assertEqual("化忌", fragment["facts"]["break_check"]["break_star_list"][0]["transformation"])

    def test_strict_jia_gui_outputs_subtypes_and_pattern_snapshot(self):
        chart = make_chart()
        chart["si_zhu"] = {"year": "丙午"}
        chart["palaces"][5]["gan_zhi"] = "甲辰"
        chart["palaces"][5]["is_body_palace"] = True
        chart["palaces"][4]["fu_xing_detail"] = [{"name": "天魁"}]
        chart["palaces"][4]["zhu_xing"] = [{"name": "廉贞", "si_hua": "化禄"}]
        chart["palaces"][6]["fu_xing_detail"] = [{"name": "天钺"}]
        chart["palaces"][6]["zhu_xing"] = [{"name": "破军", "si_hua": "化权"}]

        result = self.analyze(chart, {"focus_palaces": ["命宫"]})
        patterns = [item for item in result["fragments"] if item["type"] == "pattern"]
        jia_gui = next(
            item for item in patterns
            if item["facts"]["rule_id"] == "pattern.jia_gui_jia_lu.flanking"
        )

        self.assertEqual(2, jia_gui["facts"]["matched_variant_count"])
        self.assertEqual(
            {"bing_ding_ren_gui_chen_xu_kui_yue", "ke_quan_lu_flank"},
            {item["id"] for item in jia_gui["facts"]["matched_variants"]},
        )
        self.assertEqual(["ming", "body"], jia_gui["facts"]["target"]["roles"])
        self.assertEqual("化禄", jia_gui["facts"]["transformation_distribution"]["left"][0]["transformation"])
        self.assertEqual([], jia_gui["modifiers"]["breakers"])

    def test_non_ming_body_flanking_is_observation_only(self):
        chart = make_chart()
        chart["si_zhu"] = {"year": "丙午"}
        chart["palaces"][5]["fu_xing_detail"] = [{"name": "天魁"}]
        chart["palaces"][5]["zhu_xing"] = [{"name": "廉贞", "si_hua": "化禄"}]
        chart["palaces"][7]["fu_xing_detail"] = [{"name": "天钺"}]
        chart["palaces"][7]["zhu_xing"] = [{"name": "破军", "si_hua": "化权"}]

        result = self.analyze(chart, {"focus_palaces": ["父母宫"]})
        jia_gui_patterns = [
            item for item in result["fragments"]
            if item["type"] == "pattern"
            and item["facts"]["rule_id"] == "pattern.jia_gui_jia_lu.flanking"
        ]
        observations = [
            item for item in result["fragments"]
            if item["type"] == "pattern_observation"
            and item["facts"]["rule_id"] == "pattern.jia_gui_jia_lu.flanking"
        ]

        self.assertEqual([], jia_gui_patterns)
        self.assertEqual(2, len(observations))
        self.assertTrue(all(not item["facts"]["is_pattern_match"] for item in observations))
        self.assertTrue(all(item["fragment_id"] in result["palaces"][0]["sections"]["palace_rules"] for item in observations))

    def test_changqu_subtypes_and_breaker_locations_reach_analysis_output(self):
        chart = make_chart()
        chart["si_zhu"] = {"year": "己巳"}
        for index in (4, 5, 6):
            chart["palaces"][index]["sha_xing_detail"] = []
        chart["palaces"][4]["zhu_xing"] = [{"name": "太阳"}]
        chart["palaces"][4]["fu_xing_detail"] = [{"name": "文昌"}]
        chart["palaces"][6]["zhu_xing"] = [{"name": "太阴"}]
        chart["palaces"][6]["fu_xing_detail"] = [{"name": "文曲"}]
        chart["palaces"][1]["sha_xing_detail"] = [{"name": "擎羊"}]

        formed = self.analyze(chart, {"focus_palaces": ["命宫"]})
        formed_pattern = next(
            item for item in formed["fragments"]
            if item["type"] == "pattern"
            and item["facts"]["rule_id"] == "pattern.changqu.flanking"
        )
        self.assertEqual("formed", formed_pattern["facts"]["status"])
        self.assertEqual(1, formed_pattern["facts"]["matched_variant_count"])
        self.assertEqual([], formed_pattern["modifiers"]["breakers"])
        self.assertIn("擎羊", {
            item["star"]
            for item in formed_pattern["facts"]["malefic_notes"]["four_directions"]
        })

        chart["palaces"][6]["sha_xing_detail"] = [{"name": "铃星"}]
        broken = self.analyze(chart, {"focus_palaces": ["命宫"]})
        broken_pattern = next(
            item for item in broken["fragments"]
            if item["type"] == "pattern"
            and item["facts"]["rule_id"] == "pattern.changqu.flanking"
        )
        self.assertEqual("broken", broken_pattern["facts"]["status"])
        self.assertEqual(
            "right_flank_kong_jie_yang_ling",
            broken_pattern["modifiers"]["breakers"][0]["condition_id"],
        )
        self.assertEqual(
            "父母宫",
            broken_pattern["modifiers"]["breakers"][0]["evidence"][0]["physical_palace"],
        )

    def test_xiong_su_qian_yuan_positions_and_downgrade_reach_analysis_output(self):
        chart = make_chart()
        chart["palaces"][5]["gan_zhi"] = "乙未"
        chart["palaces"][5]["zhu_xing"] = [
            {"name": "廉贞", "liang_du": "利", "si_hua": "化忌"},
            {"name": "七杀", "liang_du": "庙"},
        ]

        result = self.analyze(chart, {"focus_palaces": ["命宫"]})
        pattern = next(
            item for item in result["fragments"]
            if item["type"] == "pattern"
            and item["facts"]["rule_id"] == "pattern.xiong_su_qian_yuan"
        )

        self.assertEqual("broken", pattern["facts"]["status"])
        self.assertEqual("formed", pattern["facts"]["base_status"])
        self.assertEqual(
            "lianzhen_qisha_together_in_wei",
            pattern["facts"]["matched_variants"][0]["id"],
        )
        self.assertEqual(
            {("廉贞", "未"), ("七杀", "未")},
            {(item["star"], item["physical_branch"]) for item in pattern["facts"]["star_positions"]},
        )
        self.assertIn("格局触发降级", pattern["facts"]["status_message"])
        self.assertTrue(any("陷地条件不可达" in note for note in pattern["facts"]["rule_notes"]))

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
        palace = result["palaces"][0]
        borrow_fragment = next(
            fragment for fragment in result["fragments"]
            if fragment.get("facts", {}).get("rule_id") == "palace.empty.borrow_opposite"
        )
        self.assertIn(borrow_fragment["fragment_id"], palace["sections"]["palace_rules"])
        self.assertNotIn(borrow_fragment["fragment_id"], palace["sections"]["patterns"])

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
        chart["palaces"][5]["gan_zhi"] = "甲寅"
        result = self.analyze(chart, {"focus_palaces": ["命宫"]})
        patterns = [
            fragment for fragment in result["fragments"]
            if fragment.get("facts", {}).get("rule_id") == "pattern.zi_fu_tong_lin"
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

    def test_legacy_sanqi_pattern_id_is_not_emitted(self):
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
        self.assertFalse(any(
            fragment.get("facts", {}).get("rule_id")
            in {"pattern.sanqi.four_directions", "pattern.san_ji_jia_hui"}
            for fragment in result["fragments"]
        ))

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
