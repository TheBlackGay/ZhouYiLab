import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "web"))

from ziwei_pattern_engine import (  # noqa: E402
    PatternConfigError,
    load_pattern_catalog,
    match_pattern,
    match_pattern_observations,
    run_catalog_examples,
)


PATTERN_DIR = PROJECT_ROOT / "config" / "ziwei" / "patterns"


def star(name, transformation=None, source_layer="natal", palace="命宫"):
    return {
        "name": name,
        "transformation": transformation,
        "source_layer": source_layer,
        "physical_palace": palace,
        "relation": "self",
    }


def context(
    focus="命宫", layer="natal", chart=None, branch=None, roles=None,
    pattern_inputs=None, **scopes
):
    defaults = {
        "self": {"stars": []},
        "triads": {"stars": []},
        "opposite": {"stars": []},
        "four_directions": {"stars": []},
        "adjacent_left": {"stars": []},
        "adjacent_right": {"stars": []},
    }
    defaults.update(scopes)
    return {
        "layer": {"id": layer, "name": layer},
        "pattern_inputs": pattern_inputs or {},
        "chart": chart or {"birth_year_stem": None, "palaces": []},
        "focus": {
            "name": focus,
            "branch": branch,
            "roles": roles if roles is not None else (["ming"] if focus == "命宫" else []),
            "effect_subject": [f"{focus}主题"],
        },
        "scopes": defaults,
    }


def base_pattern():
    return {
        "schema_version": "1.0.0",
        "id": "pattern.test",
        "revision": 1,
        "enabled": True,
        "name": "测试格局",
        "category": "test",
        "school": "测试",
        "strictness": "strict",
        "applicable_layers": ["natal"],
        "applicable_focus_palaces": ["*"],
        "required": {
            "all": [{
                "id": "required_star",
                "name": "必要星曜",
                "predicate": "star.contains",
                "scope": "self",
                "values": ["紫微"],
            }]
        },
        "enhancers": [],
        "weakeners": [],
        "breakers": [],
        "status_policy": {
            "required_matched": "formed",
            "enhancer_matched": "strengthened",
            "weakener_matched": "weakened",
            "breaker_matched": "broken",
            "tendency_matched": "tendency",
        },
        "result": {
            "nature": "neutral",
            "summary": "测试",
            "interpretation_template": "测试",
        },
        "examples": [{
            "name": "最小正例",
            "context": context(self={"stars": [star("紫微")]}),
            "expected": {"matched": True},
        }],
    }


class ZiWeiPatternEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_pattern_catalog(PATTERN_DIR)

    def test_all_embedded_examples_pass(self):
        failures = [case for case in run_catalog_examples(self.catalog) if not case["passed"]]
        self.assertEqual([], failures)

    def test_same_pattern_is_attributed_to_each_focus_palace(self):
        pattern = deepcopy(base_pattern())
        life = match_pattern(pattern, context("命宫", self={"stars": [star("紫微")]}))
        parents = match_pattern(pattern, context("父母宫", self={"stars": [star("紫微")]}))
        self.assertEqual("命宫", life["effect_palace"])
        self.assertEqual("父母宫", parents["effect_palace"])
        self.assertNotEqual(life["effect_subject"], parents["effect_subject"])

    def test_same_palace_predicate_honors_explicit_scope_and_defaults_to_self(self):
        pattern = deepcopy(base_pattern())
        pattern["required"]["all"][0] = {
            "id": "opposite_pair",
            "name": "对宫日月同宫",
            "predicate": "star.same_palace",
            "scope": "opposite",
            "values": ["太阳", "太阴"],
            "source_layer": "$current_layer",
        }
        scoped = match_pattern(pattern, context(
            self={"stars": []},
            opposite={"stars": [star("太阳"), star("太阴")]},
        ))
        pattern["required"]["all"][0].pop("scope")
        default_self = match_pattern(pattern, context(
            self={"stars": []},
            opposite={"stars": [star("太阳"), star("太阴")]},
        ))
        self.assertEqual("formed", scoped["status"])
        self.assertIsNone(default_self)

    def test_transformations_from_different_layers_cannot_form_pattern(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.san_ji_jia_hui"
        )
        result = match_pattern(pattern, context(
            layer="annual",
            four_directions={"stars": [
                star("廉贞", "化禄", "natal"),
                star("破军", "化权", "decade"),
                star("武曲", "化科", "annual"),
            ]},
        ))
        self.assertIsNone(result)

    def test_jia_gui_strict_subtypes_one_and_three_can_match_together(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.jia_gui_jia_lu.flanking"
        )
        result = match_pattern(pattern, context(
            focus="命宫",
            branch="辰",
            roles=["ming"],
            chart={"birth_year_stem": "丙", "palaces": []},
            adjacent_left={"stars": [
                star("天魁", palace="兄弟宫"),
                star("廉贞", "化禄", palace="兄弟宫"),
            ]},
            adjacent_right={"stars": [
                star("天钺", palace="父母宫"),
                star("破军", "化权", palace="父母宫"),
            ]},
        ))
        self.assertEqual("命宫", result["effect_palace"])
        self.assertEqual("formed", result["status"])
        self.assertEqual(2, result["matched_variant_count"])
        self.assertEqual(
            {"bing_ding_ren_gui_chen_xu_kui_yue", "ke_quan_lu_flank"},
            {item["id"] for item in result["matched_variants"]},
        )
        distribution = result["pattern_snapshot"]["transformation_distribution"]
        self.assertEqual("化禄", distribution["left"][0]["transformation"])
        self.assertEqual("化权", distribution["right"][0]["transformation"])

    def test_jia_gui_never_matches_non_ming_non_body_palace(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.jia_gui_jia_lu.flanking"
        )
        result = match_pattern(pattern, context(
            focus="父母宫",
            branch="辰",
            roles=[],
            chart={"birth_year_stem": "丙", "palaces": []},
            adjacent_left={"stars": [
                star("天魁"), star("廉贞", "化禄"),
            ]},
            adjacent_right={"stars": [
                star("天钺"), star("破军", "化权"),
            ]},
        ))
        self.assertIsNone(result)

    def test_ming_shen_lu_cun_template_uses_actual_lu_cun_position(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.jia_gui_jia_lu.flanking"
        )
        chart = {
            "birth_year_stem": "辛",
            "ming": {"branch": "戌"},
            "body": {"branch": "申"},
            "palaces": [{
                "index": 8,
                "name": "某宫",
                "branch": "酉",
                "stars": [star("禄存", palace="某宫")],
            }],
        }
        result = match_pattern(pattern, context(
            focus="命宫", branch="戌", roles=["ming"], chart=chart
        ))
        self.assertEqual("formed", result["status"])
        self.assertEqual("ming_shen_flank_lu_cun", result["matched_variants"][0]["id"])
        self.assertEqual("酉", result["pattern_snapshot"]["lu_cun_positions"][0]["branch"])

    def test_malefics_are_notes_and_never_break_jia_gui(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.jia_gui_jia_lu.flanking"
        )
        malefic = {**star("擎羊"), "category": "malefic"}
        result = match_pattern(pattern, context(
            branch="戌",
            chart={"birth_year_stem": "丁", "palaces": []},
            self={"stars": [malefic]},
            adjacent_left={"stars": [star("天魁"), {**star("火星"), "category": "malefic"}]},
            adjacent_right={"stars": [star("天钺")]},
        ))
        self.assertEqual("formed", result["status"])
        self.assertEqual([], result["breakers"])
        self.assertEqual("擎羊", result["pattern_snapshot"]["malefic_notes"]["target"][0]["star"])
        self.assertEqual("火星", result["pattern_snapshot"]["malefic_notes"]["adjacent"][0]["star"])

    def test_ordinary_palace_flanking_is_observation_not_pattern(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.jia_gui_jia_lu.flanking"
        )
        ordinary = context(
            focus="父母宫",
            roles=[],
            adjacent_left={"stars": [star("天魁"), star("廉贞", "化禄")]},
            adjacent_right={"stars": [star("天钺"), star("破军", "化权")]},
        )
        notes = match_pattern_observations(pattern, ordinary)
        self.assertIsNone(match_pattern(pattern, ordinary))
        self.assertEqual(2, len(notes))
        self.assertTrue(all("不构成夹贵夹禄格" in item["note"] for item in notes))
        self.assertEqual([], match_pattern_observations(
            pattern,
            context(
                focus="夫妻宫",
                roles=["body"],
                adjacent_left=ordinary["scopes"]["adjacent_left"],
                adjacent_right=ordinary["scopes"]["adjacent_right"],
            ),
        ))

    def test_transformations_on_one_side_do_not_form_flank(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.jia_gui_jia_lu.flanking"
        )
        result = match_pattern(pattern, context(
            adjacent_left={"stars": [
                star("破军", "化权"), star("武曲", "化科")
            ]},
        ))
        self.assertIsNone(result)

    def test_stars_from_different_layers_do_not_form_flank(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.jia_gui_jia_lu.flanking"
        )
        result = match_pattern(pattern, context(
            layer="annual",
            adjacent_left={"stars": [star("天魁", source_layer="natal")]},
            adjacent_right={"stars": [star("天钺", source_layer="annual")]},
        ))
        self.assertIsNone(result)

    def test_changqu_pattern_no_longer_matches_sun_moon_flank(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.changqu.flanking"
        )
        result = match_pattern(pattern, context(
            focus="命宫",
            roles=["ming"],
            adjacent_left={"stars": [star("太阳", palace="兄弟宫")]},
            adjacent_right={"stars": [star("太阴", palace="父母宫")]},
        ))
        self.assertIsNone(result)

    def test_changqu_breakers_check_target_and_both_flanking_palaces(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.changqu.flanking"
        )
        adjacent_malefic = match_pattern(pattern, context(
            self={"stars": []},
            adjacent_left={"stars": [star("文昌"), star("铃星", palace="兄弟宫")]},
            adjacent_right={"stars": [star("文曲")]},
        ))
        focus_malefic = match_pattern(pattern, context(
            self={"stars": [star("地空", palace="命宫")]},
            adjacent_left={"stars": [star("文昌")]},
            adjacent_right={"stars": [star("文曲")]},
        ))
        self.assertEqual("broken", adjacent_malefic["status"])
        self.assertEqual("broken", focus_malefic["status"])
        self.assertEqual(
            "left_flank_kong_jie_yang_ling",
            adjacent_malefic["breakers"][0]["condition_id"],
        )
        self.assertEqual("兄弟宫", adjacent_malefic["breakers"][0]["evidence"][0]["physical_palace"])
        self.assertEqual(
            "target_kong_jie_yang_ling",
            focus_malefic["breakers"][0]["condition_id"],
        )

    def test_changqu_triads_malefic_is_note_not_breaker(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.changqu.flanking"
        )
        result = match_pattern(pattern, context(
            adjacent_left={"stars": [star("文昌")]},
            adjacent_right={"stars": [star("文曲")]},
            four_directions={"stars": [{
                **star("擎羊", palace="财帛宫"), "category": "malefic",
            }]},
        ))
        self.assertEqual("formed", result["status"])
        self.assertEqual([], result["breakers"])
        self.assertEqual("four_directions_malefics_note", result["matched_observations"][0]["condition_id"])

    def test_changqu_on_ordinary_palace_is_observation_only(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.changqu.flanking"
        )
        ordinary = context(
            focus="财帛宫",
            roles=[],
            adjacent_left={"stars": [star("太阳"), star("文昌")]},
            adjacent_right={"stars": [star("太阴"), star("文曲")]},
        )
        notes = match_pattern_observations(pattern, ordinary)
        self.assertIsNone(match_pattern(pattern, ordinary))
        self.assertEqual(1, len(notes))
        self.assertIn("不构成昌曲夹命格", notes[0]["note"])

    def test_xiong_su_branch_b_records_lianzhen_without_requiring_its_location(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.xiong_su_qian_yuan"
        )
        qisha = {**star("七杀", palace="夫妻宫"), "brightness": "旺", "physical_branch": "午"}
        lianzhen = {**star("廉贞", palace="财帛宫"), "brightness": "庙", "physical_branch": "申"}
        result = match_pattern(pattern, context(
            focus="夫妻宫",
            branch="午",
            roles=["body"],
            self={"stars": [qisha]},
            chart={"palaces": [
                {"name": "夫妻宫", "branch": "午", "stars": [qisha]},
                {"name": "财帛宫", "branch": "申", "stars": [lianzhen]},
            ]},
        ))
        self.assertEqual("formed", result["status"])
        self.assertEqual("qisha_in_wu_ming_shen", result["matched_variants"][0]["id"])
        positions = {item["star"]: item["physical_branch"] for item in result["pattern_snapshot"]["star_positions"]}
        self.assertEqual({"七杀": "午", "廉贞": "申"}, positions)

    def test_xiong_su_lianzhen_huaji_anywhere_breaks_but_keeps_base_match(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.xiong_su_qian_yuan"
        )
        qisha = {**star("七杀", palace="夫妻宫"), "brightness": "旺", "physical_branch": "午"}
        lianzhen = {
            **star("廉贞", "化忌", palace="财帛宫"),
            "brightness": "庙",
            "physical_branch": "申",
        }
        result = match_pattern(pattern, context(
            focus="夫妻宫",
            branch="午",
            roles=["body"],
            self={"stars": [qisha]},
            chart={"palaces": [
                {"name": "夫妻宫", "branch": "午", "stars": [qisha]},
                {"name": "财帛宫", "branch": "申", "stars": [lianzhen]},
            ]},
        ))
        self.assertTrue(result["required_trace"]["matched"])
        self.assertEqual("formed", result["base_status"])
        self.assertEqual("broken", result["status"])
        self.assertEqual("lianzhen_huaji_anywhere", result["breakers"][0]["condition_id"])
        self.assertIn("格局触发降级", result["status_message"])
        self.assertTrue(any("陷地条件不可达" in note for note in result["rule_notes"]))

    def test_xiong_su_never_matches_ordinary_palace_or_neighbor_misreading(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.xiong_su_qian_yuan"
        )
        ordinary = match_pattern(pattern, context(
            focus="财帛宫",
            branch="未",
            roles=[],
            self={"stars": [star("廉贞"), star("七杀")]},
        ))
        neighbor = match_pattern(pattern, context(
            focus="命宫",
            branch="未",
            roles=["ming"],
            self={"stars": [star("廉贞")]},
            adjacent_left={"stars": [star("七杀")]},
        ))
        self.assertIsNone(ordinary)
        self.assertIsNone(neighbor)

    def test_wutan_requires_wu_qu_tan_lang_in_ming_or_body_at_chou_wei(self):
        pattern = next(item for item in self.catalog["patterns"] if item["id"] == "pattern.wu_tan_pattern")
        formed = match_pattern(pattern, context(
            focus="命宫", branch="丑", roles=["ming"],
            self={"stars": [star("武曲"), star("贪狼")]},
        ))
        ordinary = match_pattern(pattern, context(
            focus="财帛宫", branch="丑", roles=[],
            self={"stars": [star("武曲"), star("贪狼")]},
        ))
        self.assertEqual("formed", formed["status"])
        self.assertIsNone(ordinary)

    def test_wutan_three_fang_support_strengthens_without_being_required(self):
        pattern = next(item for item in self.catalog["patterns"] if item["id"] == "pattern.wu_tan_pattern")
        result = match_pattern(pattern, context(
            focus="夫妻宫", branch="未", roles=["body"],
            self={"stars": [star("武曲"), star("贪狼")]},
            triads={"stars": [star("左辅")]},
        ))
        self.assertEqual("strengthened", result["status"])
        self.assertEqual("san_fang_chang_qu_zuo_you", result["enhancers"][0]["condition_id"])

    def test_wutan_decade_ke_quan_lu_is_layer_scoped(self):
        pattern = next(item for item in self.catalog["patterns"] if item["id"] == "pattern.wu_tan_pattern")
        decade = match_pattern(pattern, context(
            layer="decade", focus="命宫", branch="未", roles=["ming"],
            self={"stars": [star("武曲", source_layer="decade"), star("贪狼", source_layer="decade")]},
            four_directions={"stars": [
                star("廉贞", "化禄", source_layer="decade"),
                star("破军", "化权", source_layer="decade"),
                star("武曲", "化科", source_layer="decade"),
            ]},
        ))
        natal = match_pattern(pattern, context(
            layer="natal", focus="命宫", branch="未", roles=["ming"],
            self={"stars": [star("武曲"), star("贪狼")]},
            four_directions={"stars": [
                star("廉贞", "化禄"), star("破军", "化权"), star("武曲", "化科"),
            ]},
        ))
        self.assertEqual("strengthened", decade["status"])
        self.assertTrue(any(item["condition_id"] == "decade_ke_quan_lu" for item in decade["enhancers"]))
        self.assertEqual("formed", natal["status"])
        self.assertFalse(natal["enhancers"])

    def test_qisha_chao_dou_flags_auspicious_stars_and_auspicious_limit(self):
        pattern = next(item for item in self.catalog["patterns"] if item["id"] == "pattern.qi_sha_chao_dou")
        result = match_pattern(pattern, {
            "layer": {"id": "decade", "name": "大限", "is_auspicious_limit": True},
            "chart": {"palaces": []},
            "focus": {"name": "命宫", "branch": "午", "roles": ["ming"], "effect_subject": ["盘主自身"]},
            "scopes": {
                "self": {"stars": [{"name": "廉贞", "source_layer": "decade"}, {"name": "七杀", "source_layer": "decade"}]},
                "triads": {"stars": [{"name": "左辅", "source_layer": "decade"}]},
                "opposite": {"stars": []}, "four_directions": {"stars": []},
                "adjacent_left": {"stars": []}, "adjacent_right": {"stars": []},
            },
        })
        self.assertEqual("strengthened", result["status"])
        self.assertEqual({"has_auspicious": True, "is_auspicious_limit": True}, result["flags"])

    def test_ri_yue_tong_lin_requires_sun_and_moon_in_opposite_of_chou_wei_ming(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.ri_yue_tong_lin"
        )
        result = match_pattern(pattern, context(
            focus="命宫",
            branch="丑",
            roles=["ming"],
            chart={"birth_year_stem": "乙", "palaces": []},
            opposite={"stars": [
                {**star("太阳", palace="迁移宫"), "physical_branch": "未"},
                {**star("太阴", palace="迁移宫"), "physical_branch": "未"},
            ]},
        ))
        self.assertEqual("formed", result["status"])
        self.assertEqual({"bing_xin_bonus": False}, result["flags"])
        opposite_evidence = next(
            item for item in result["matched_conditions"]
            if item["condition_id"] == "ri_yue_in_opposite"
        )["evidence"]
        self.assertEqual({"太阳", "太阴"}, {item["star"] for item in opposite_evidence})
        self.assertEqual({"未"}, {item["physical_branch"] for item in opposite_evidence})

    def test_ri_yue_tong_lin_bing_xin_bonus_and_body_observation(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.ri_yue_tong_lin"
        )
        opposite = {"stars": [star("太阳"), star("太阴")]}
        ming = match_pattern(pattern, context(
            focus="命宫",
            branch="未",
            roles=["ming"],
            chart={"birth_year_stem": "辛", "palaces": []},
            opposite=opposite,
        ))
        body_context = context(
            focus="夫妻宫",
            branch="未",
            roles=["body"],
            chart={"birth_year_stem": "辛", "palaces": []},
            opposite=opposite,
        )
        self.assertEqual("strengthened", ming["status"])
        self.assertEqual({"bing_xin_bonus": True}, ming["flags"])
        self.assertIsNone(match_pattern(pattern, body_context))
        observations = match_pattern_observations(pattern, body_context)
        self.assertEqual(1, len(observations))
        self.assertIn("原文只论命宫", observations[0]["note"])

    def test_ling_tan_grade_requires_both_zi_chen_and_external_auspicious_flag(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.ling_tan_ge"
        )
        ling_tan = {"stars": [star("贪狼"), star("铃星")]}
        zi_without_flag = match_pattern(pattern, context(
            branch="子", chart={"birth_year_stem": "乙", "palaces": []},
            self=ling_tan,
        ))
        zi_with_flag = match_pattern(pattern, context(
            branch="子", chart={"birth_year_stem": "乙", "palaces": []},
            pattern_inputs={"pattern.ling_tan_ge": {"has_auspicious": True}},
            self=ling_tan,
        ))
        xu_with_flag = match_pattern(pattern, context(
            branch="戌", chart={"birth_year_stem": "乙", "palaces": []},
            pattern_inputs={"pattern.ling_tan_ge": {"has_auspicious": True}},
            self=ling_tan,
        ))
        self.assertEqual(("formed", "普通", False), (
            zi_without_flag["status"], zi_without_flag["grade"],
            zi_without_flag["flags"]["has_auspicious"],
        ))
        self.assertEqual(("strengthened", "佳", True), (
            zi_with_flag["status"], zi_with_flag["grade"],
            zi_with_flag["flags"]["has_auspicious"],
        ))
        self.assertEqual(("strengthened", "普通"), (
            xu_with_flag["status"], xu_with_flag["grade"],
        ))

    def test_ling_tan_uses_natal_wu_ji_stem_in_decade_and_body_is_observation(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.ling_tan_ge"
        )
        decade_stars = {"stars": [
            star("贪狼", source_layer="decade"),
            star("铃星", source_layer="decade"),
        ]}
        decade = match_pattern(pattern, context(
            layer="decade", branch="未",
            chart={"birth_year_stem": "己", "palaces": []},
            self=decade_stars,
        ))
        body_context = context(
            focus="夫妻宫", branch="辰", roles=["body"],
            chart={"birth_year_stem": "己", "palaces": []},
            self={"stars": [star("贪狼"), star("铃星")]},
        )
        self.assertEqual("strengthened", decade["status"])
        self.assertEqual("普通", decade["grade"])
        self.assertTrue(decade["flags"]["wu_ji_bonus"])
        self.assertIsNone(match_pattern(pattern, body_context))
        observations = match_pattern_observations(pattern, body_context)
        self.assertEqual(1, len(observations))
        self.assertIn("原文只写安命", observations[0]["note"])

    def test_huo_tan_preserves_grade_and_break_evidence_when_broken(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.huo_tan_ge"
        )
        result = match_pattern(pattern, context(
            branch="未",
            self={"stars": [
                star("贪狼"), star("火星"),
                {**star("地空", palace="命宫"), "physical_branch": "未"},
            ]},
            triads={"stars": [
                {**star("擎羊", palace="财帛宫"), "physical_branch": "亥"},
            ]},
        ))
        self.assertEqual("formed", result["base_status"])
        self.assertEqual("broken", result["status"])
        self.assertEqual("上格", result["grade"])
        self.assertEqual("broken", result["break_check"]["status"])
        self.assertEqual(
            {("地空", "命宫", "未"), ("擎羊", "财帛宫", "亥")},
            {
                (item["star"], item["palace"], item["branch"])
                for item in result["break_check"]["break_star_list"]
            },
        )

    def test_huo_tan_external_jihua_does_not_form_invalid_branch_or_change_grade(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.huo_tan_ge"
        )
        stars = {"stars": [star("贪狼"), star("火星")]}
        pattern_inputs = {"pattern.huo_tan_ge": {"has_jihua": True}}
        lower = match_pattern(pattern, context(
            branch="卯", pattern_inputs=pattern_inputs, self=stars,
        ))
        invalid_branch = match_pattern(pattern, context(
            branch="子", pattern_inputs=pattern_inputs, self=stars,
        ))
        self.assertEqual("strengthened", lower["status"])
        self.assertEqual("次格", lower["grade"])
        self.assertTrue(lower["flags"]["has_jihua"])
        self.assertEqual("normal", lower["break_check"]["status"])
        self.assertIsNone(invalid_branch)

    def test_huo_tan_body_is_observation_not_pattern(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.huo_tan_ge"
        )
        body_context = context(
            focus="夫妻宫", branch="辰", roles=["body"],
            self={"stars": [star("贪狼"), star("火星")]},
        )
        self.assertIsNone(match_pattern(pattern, body_context))
        observations = match_pattern_observations(pattern, body_context)
        self.assertEqual(1, len(observations))
        self.assertIn("不触发火贪格", observations[0]["note"])

    def test_zi_fu_chao_yuan_allows_swapped_stars_but_rejects_same_palace(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.zi_fu_chao_yuan_ge"
        )

        def palace(branch, *stars):
            return {
                "name": f"{branch}宫",
                "branch": branch,
                "stars": [
                    {**star(name, palace=f"{branch}宫"), "physical_branch": branch}
                    for name in stars
                ],
            }

        swapped = match_pattern(pattern, context(
            branch="寅",
            chart={"palaces": [palace("午", "天府"), palace("戌", "紫微")]},
        ))
        same_palace = match_pattern(pattern, context(
            branch="寅",
            chart={"palaces": [palace("午", "紫微", "天府"), palace("戌")]},
        ))
        self.assertEqual("formed", swapped["status"])
        self.assertEqual("普通吉格", swapped["grade"])
        self.assertEqual(
            {"zi_palace": "戌", "fu_palace": "午"},
            swapped["named_star_positions"],
        )
        self.assertIsNone(same_palace)

    def test_zi_fu_chao_yuan_qisha_grade_and_huaji_break_break_evidence(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.zi_fu_chao_yuan_ge"
        )
        ziwei = {
            **star("紫微", "化忌", source_layer="decade", palace="财帛宫"),
            "physical_branch": "辰",
        }
        tianfu = {
            **star("天府", source_layer="decade", palace="官禄宫"),
            "physical_branch": "子",
        }
        result = match_pattern(pattern, context(
            layer="decade", branch="申",
            pattern_inputs={"pattern.zi_fu_chao_yuan_ge": {"has_liu_lu": True}},
            chart={"palaces": [
                {"name": "官禄宫", "branch": "子", "stars": [tianfu]},
                {"name": "财帛宫", "branch": "辰", "stars": [ziwei]},
            ]},
            self={"stars": [star("七杀", source_layer="decade")]},
            triads={"stars": [tianfu, ziwei]},
        ))
        self.assertEqual("formed", result["base_status"])
        self.assertEqual("broken", result["status"])
        self.assertEqual("上格", result["grade"])
        self.assertTrue(result["flags"]["has_liu_lu"])
        self.assertEqual([{
            "star": "紫微",
            "transformation": "化忌",
            "palace": "财帛宫",
            "branch": "辰",
        }], result["break_check"]["break_star_list"])

    def test_zi_fu_chao_yuan_body_is_observation_only(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.zi_fu_chao_yuan_ge"
        )
        chart = {"palaces": [
            {"name": "午宫", "branch": "午", "stars": [{
                **star("紫微", palace="午宫"), "physical_branch": "午",
            }]},
            {"name": "戌宫", "branch": "戌", "stars": [{
                **star("天府", palace="戌宫"), "physical_branch": "戌",
            }]},
        ]}
        body_context = context(
            focus="夫妻宫", branch="寅", roles=["body"], chart=chart,
        )
        self.assertIsNone(match_pattern(pattern, body_context))
        observations = match_pattern_observations(pattern, body_context)
        self.assertEqual(1, len(observations))
        self.assertIn("不触发紫府朝垣格", observations[0]["note"])

    def test_modifier_precedence_is_breaker_then_weakener_then_enhancer(self):
        pattern = base_pattern()
        for group, value in (
            ("enhancers", "左辅"), ("weakeners", "火星"), ("breakers", "化忌")
        ):
            pattern[group] = [{
                "id": group,
                "name": group,
                "predicate": "star.contains",
                "scope": "four_directions",
                "values": [value],
            }]
        result = match_pattern(pattern, context(
            self={"stars": [star("紫微")]},
            four_directions={"stars": [star("左辅"), star("火星"), star("化忌")]},
        ))
        self.assertEqual("broken", result["status"])
        self.assertTrue(result["enhancers"])
        self.assertTrue(result["weakeners"])
        self.assertTrue(result["breakers"])

    def test_tendency_requires_explicit_condition(self):
        pattern = base_pattern()
        no_match = match_pattern(pattern, context(self={"stars": [star("天府")]}))
        self.assertIsNone(no_match)
        pattern["tendency_conditions"] = {
            "all": [{
                "id": "tendency_star",
                "name": "倾向星曜",
                "predicate": "star.contains",
                "scope": "self",
                "values": ["天府"],
            }]
        }
        tendency = match_pattern(pattern, context(self={"stars": [star("天府")]}))
        self.assertEqual("tendency", tendency["status"])

    def test_match_contains_condition_trace_and_star_evidence(self):
        result = match_pattern(
            base_pattern(), context(self={"stars": [star("紫微", palace="父母宫")]})
        )
        self.assertTrue(result["required_trace"]["matched"])
        leaf = result["matched_conditions"][0]
        self.assertEqual("required_star", leaf["condition_id"])
        self.assertEqual("紫微", leaf["evidence"][0]["star"])
        self.assertEqual("父母宫", leaf["evidence"][0]["physical_palace"])

    def test_invalid_catalogs_fail_validation(self):
        invalid_cases = []
        unknown_predicate = base_pattern()
        unknown_predicate["required"]["all"][0]["predicate"] = "python.eval"
        invalid_cases.append((unknown_predicate, "不支持谓词"))
        invalid_layer = base_pattern()
        invalid_layer["applicable_layers"] = ["future"]
        invalid_cases.append((invalid_layer, "不支持的盘层"))
        invalid_scope = base_pattern()
        invalid_scope["required"]["all"][0]["scope"] = "nearby"
        invalid_cases.append((invalid_scope, "scope 无效"))
        invalid_status = base_pattern()
        invalid_status["status_policy"]["required_matched"] = "maybe"
        invalid_cases.append((invalid_status, "状态无效"))
        invalid_variant_policy = base_pattern()
        invalid_variant_policy["required_variant_policy"] = {
            "minimum_matches": 1,
            "status": "strengthened",
        }
        invalid_cases.append((invalid_variant_policy, "至少为 2"))
        invalid_external_input = base_pattern()
        invalid_external_input["required"]["all"][0] = {
            "id": "bad_external_input",
            "predicate": "input.pattern_flag",
            "pattern_id": "not-a-pattern-id",
            "key": "flag",
            "value": True,
        }
        invalid_cases.append((invalid_external_input, "外部格局布尔输入配置无效"))
        invalid_break_check = base_pattern()
        invalid_break_check["break_check"] = {
            "break_star": "擎羊",
            "scan_scope": "命宫",
            "note": "测试",
        }
        invalid_cases.append((invalid_break_check, "break_check 配置无效"))

        for pattern, message in invalid_cases:
            with self.subTest(message=message):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / "_manifest.json").write_text(json.dumps({
                        "schema_version": "1.0.0",
                        "ruleset": "test",
                        "pattern_count": 1,
                    }), encoding="utf-8")
                    (root / "rule.json").write_text(
                        json.dumps(pattern, ensure_ascii=False), encoding="utf-8"
                    )
                    with self.assertRaisesRegex(PatternConfigError, message):
                        load_pattern_catalog(root)

    def test_duplicate_pattern_ids_fail_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "_manifest.json").write_text(json.dumps({
                "schema_version": "1.0.0",
                "ruleset": "test",
                "pattern_count": 2,
            }), encoding="utf-8")
            payload = json.dumps(base_pattern(), ensure_ascii=False)
            (root / "one.json").write_text(payload, encoding="utf-8")
            (root / "two.json").write_text(payload, encoding="utf-8")
            with self.assertRaisesRegex(PatternConfigError, "格局 ID 重复"):
                load_pattern_catalog(root)


if __name__ == "__main__":
    unittest.main()
