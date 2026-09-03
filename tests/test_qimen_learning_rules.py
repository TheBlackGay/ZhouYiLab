import json
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = PROJECT_ROOT / "web" / "qimen_learning.js"


def run_rules(expression):
    script = (
        f"const rules = require({json.dumps(str(RULES_PATH))});"
        f"console.log(JSON.stringify({expression}));"
    )
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return json.loads(completed.stdout)


class QiMenLearningRuleTests(unittest.TestCase):
    def test_palace_metadata_uses_later_heaven_directions(self):
        metadata = run_rules("rules.palaceKnowledge")

        self.assertEqual(("水", "北", ["子"]), (
            metadata["1"]["element"], metadata["1"]["direction"],
            metadata["1"]["branches"],
        ))
        self.assertEqual(("火", "南", ["午"]), (
            metadata["9"]["element"], metadata["9"]["direction"],
            metadata["9"]["branches"],
        ))

    def test_five_element_relations_cover_all_directions(self):
        relations = run_rules("["
            "rules.getElementRelation('土', '土').key,"
            "rules.getElementRelation('土', '金').key,"
            "rules.getElementRelation('土', '火').key,"
            "rules.getElementRelation('土', '水').key,"
            "rules.getElementRelation('土', '木').key"
            "]")

        self.assertEqual([
            "same", "subject_generates", "target_generates",
            "subject_controls", "target_controls",
        ], relations)

    def test_shen_you_void_marks_kun_and_dui(self):
        void_palaces = run_rules(
            "Object.keys(rules.palaceKnowledge).filter(number => "
            "rules.isVoidPalace(Number(number), '申酉'))"
        )

        self.assertEqual(["2", "7"], void_palaces)

    def test_hour_horse_uses_hour_branch_three_harmony_group(self):
        horses = run_rules(
            "['子', '午', '酉', '卯'].map(branch => "
            "rules.getHourHorse(branch))"
        )

        self.assertEqual([
            {"branch": "寅", "palaceNumber": 8},
            {"branch": "申", "palaceNumber": 2},
            {"branch": "亥", "palaceNumber": 6},
            {"branch": "巳", "palaceNumber": 4},
        ], horses)

    def test_gate_pressure_means_gate_controls_palace(self):
        pressured = run_rules("["
            "rules.isGatePressured('惊', 4),"
            "rules.isGatePressured('休', 9),"
            "rules.isGatePressured('开', 6),"
            "rules.isGatePressured('生', 8)"
            "]")

        self.assertEqual([True, True, False, False], pressured)

    def test_six_instrument_punishments_cover_declared_palaces(self):
        results = run_rules("["
            "...Object.entries({戊:3,己:2,庚:8,辛:9,壬:4,癸:4})"
            ".map(([stem,palace]) => rules.isInstrumentPunishment(stem,palace)),"
            "rules.isInstrumentPunishment('戊', 2),"
            "rules.isInstrumentPunishment('乙', 6)"
            "]")

        self.assertEqual([True] * 6 + [False, False], results)

    def test_three_wonders_in_tomb_use_qian_and_gen(self):
        results = run_rules("["
            "rules.isWonderInTomb('乙', 6),"
            "rules.isWonderInTomb('丙', 6),"
            "rules.isWonderInTomb('丁', 8),"
            "rules.isWonderInTomb('乙', 2),"
            "rules.isWonderInTomb('戊', 6)"
            "]")

        self.assertEqual([True, True, True, False, False], results)

    def test_five_not_meet_requires_hour_to_control_day_with_same_yin_yang(self):
        results = run_rules("["
            "...['甲庚','乙辛','丙壬','丁癸','戊甲','己乙','庚丙','辛丁','壬戊','癸己']"
            ".map(pair => rules.isFiveNotMeet(pair[0], pair[1])),"
            "rules.isFiveNotMeet('甲', '辛'),"
            "rules.isFiveNotMeet('甲', '己'),"
            "rules.isFiveNotMeet('', '庚')"
            "]")

        self.assertEqual([True] * 10 + [False, False, False], results)

    def test_first_stem_response_batch_has_stable_pair_names(self):
        responses = run_rules("["
            "...['戊丙','丙戊','乙辛','辛乙','丁癸','癸丁','庚丙','丙庚']"
            ".map(pair => rules.getStemResponse(pair[0], pair[1])?.name),"
            "rules.getStemResponse('戊', '戊'),"
            "rules.getStemResponse('', '丙')"
            "]")

        self.assertEqual([
            "青龙返首", "飞鸟跌穴", "青龙逃走", "白虎猖狂",
            "朱雀投江", "腾蛇夭矫", "太白入荧", "荧入太白",
            None, None,
        ], responses)

    def test_jia_life_stems_resolve_from_full_year_pillar(self):
        profiles = run_rules("["
            "...['子戊','戌己','申庚','午辛','辰壬','寅癸']"
            ".map(pair => rules.resolveLifeStem('甲', pair[0])?.lookupStem),"
            "rules.resolveLifeStem('乙', '丑'),"
            "rules.resolveLifeStem('甲', '卯'),"
            "rules.resolveLifeStem('', '')"
            "]")

        self.assertEqual([
            "戊", "己", "庚", "辛", "壬", "癸",
            {"stem": "乙", "lookupStem": "乙", "hidden": False},
            None, None,
        ], profiles)

    def test_fuyin_and_fanyin_compare_entire_outer_ring(self):
        layouts = run_rules("(() => {"
            "const fixed = {1:['休','天蓬'],2:['死','天芮'],3:['伤','天冲'],"
            "4:['杜','天辅'],6:['开','天心'],7:['惊','天柱'],"
            "8:['生','天任'],9:['景','天英']};"
            "const opposite = {1:9,9:1,2:8,8:2,3:7,7:3,4:6,6:4};"
            "const fuyin = Object.entries(fixed).map(([number,values]) => "
            "({palace_num:Number(number),gate:values[0],star:values[1]}));"
            "const fanyin = Object.entries(fixed).map(([number,values]) => "
            "({palace_num:opposite[number],gate:values[0],star:values[1]}));"
            "return [rules.detectPlatePatterns(fuyin),rules.detectPlatePatterns(fanyin)];"
            "})()")

        self.assertEqual({
            "gateFuyin": True, "gateFanyin": False,
            "starFuyin": True, "starFanyin": False,
        }, layouts[0])
        self.assertEqual({
            "gateFuyin": False, "gateFanyin": True,
            "starFuyin": False, "starFanyin": True,
        }, layouts[1])


if __name__ == "__main__":
    unittest.main()
