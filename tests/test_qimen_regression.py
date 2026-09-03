import json
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = PROJECT_ROOT / "build" / "examples" / "qi_men_web_cli"


@unittest.skipUnless(CLI_PATH.exists(), "qi_men_web_cli 尚未构建")
class QiMenRegressionTests(unittest.TestCase):
    def chart(self, year, month, day, hour, minute=0):
        completed = subprocess.run(
            [str(CLI_PATH)],
            input=json.dumps({
                "calendar": "solar",
                "date": {
                    "year": year,
                    "month": month,
                    "day": day,
                    "hour": hour,
                    "minute": minute,
                },
            }),
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_2026_09_02_jia_xu_uses_jia_xu_xun(self):
        chart = self.chart(2026, 9, 2, 20, 20)

        self.assertEqual("shijia_zhuanpan_chaibu", chart["method"])
        self.assertEqual("tian_qin_with_tian_rui", chart["center_lodging"])
        self.assertEqual("甲戌", (
            chart["ba_zi"]["hour"]["stem"] + chart["ba_zi"]["hour"]["branch"]
        ))
        self.assertEqual(("阴遁", "上元", "第1局"), (
            chart["dun"], chart["yuan"], chart["ju"],
        ))
        self.assertEqual(("天英", "景", "南", "南"), (
            chart["zhi_fu_star"], chart["zhi_shi_gate"],
            chart["zhi_fu_palace"], chart["zhi_shi_palace"],
        ))

    def test_yin_one_earth_plate_and_center_are_stable(self):
        chart = self.chart(2026, 9, 2, 20, 20)
        palaces = {item["palace_num"]: item for item in chart["palaces"]}

        self.assertEqual(
            {1: "戊", 2: "乙", 3: "丙", 4: "丁", 5: "癸",
             6: "壬", 7: "辛", 8: "庚", 9: "己"},
            {number: palace["di_gan"] for number, palace in palaces.items()},
        )
        self.assertEqual("", palaces[5]["gate"])
        self.assertEqual("", palaces[5]["spirit"])
        self.assertEqual("天禽", palaces[2]["lodged_star"])
        self.assertEqual("癸", palaces[2]["lodged_tian_gan"])

    def test_2026_09_02_ren_shen_matches_reference_chart(self):
        chart = self.chart(2026, 9, 2, 16, 42)
        palaces = {item["palace_num"]: item for item in chart["palaces"]}

        self.assertEqual(("丙申", "壬申"), (
            chart["ba_zi"]["month"]["stem"] + chart["ba_zi"]["month"]["branch"],
            chart["ba_zi"]["hour"]["stem"] + chart["ba_zi"]["hour"]["branch"],
        ))
        self.assertEqual(("阴遁", "上元", "第1局"), (
            chart["dun"], chart["yuan"], chart["ju"],
        ))
        self.assertEqual(("天蓬", "西北", "休", "西南"), (
            chart["zhi_fu_star"], chart["zhi_fu_palace"],
            chart["zhi_shi_gate"], chart["zhi_shi_palace"],
        ))
        self.assertEqual(
            {1: "杜", 2: "休", 3: "死", 4: "惊",
             6: "伤", 7: "生", 8: "景", 9: "开"},
            {number: palace["gate"] for number, palace in palaces.items()
             if number != 5},
        )
        self.assertEqual(
            {
                1: ("九天", "天任", "庚", "戊"),
                2: ("太阴", "天柱", "辛", "乙"),
                3: ("玄武", "天辅", "丁", "丙"),
                4: ("白虎", "天英", "己", "丁"),
                6: ("直符", "天蓬", "戊", "壬"),
                7: ("腾蛇", "天心", "壬", "辛"),
                8: ("九地", "天冲", "丙", "庚"),
                9: ("六合", "天芮", "乙", "己"),
            },
            {
                number: (
                    palace["spirit"], palace["star"],
                    palace["tian_gan"], palace["di_gan"],
                )
                for number, palace in palaces.items() if number != 5
            },
        )
        self.assertEqual(("天禽", "癸"), (
            palaces[9]["lodged_star"], palaces[9]["lodged_tian_gan"],
        ))

    def test_rotating_plate_has_one_chief_and_eight_gates(self):
        for args in ((2026, 9, 2, 20, 20), (2011, 6, 18, 3, 56)):
            with self.subTest(args=args):
                chart = self.chart(*args)
                palaces = chart["palaces"]
                self.assertEqual(9, len(palaces))
                self.assertEqual(8, sum(bool(item["gate"]) for item in palaces))
                self.assertEqual(8, sum(bool(item["spirit"]) for item in palaces))
                chiefs = [item for item in palaces if item["spirit"] == "直符"]
                self.assertEqual(1, len(chiefs))
                self.assertEqual(chart["zhi_fu_palace"], chiefs[0]["palace_name"])
                envoy = next(
                    item for item in palaces
                    if item["palace_name"] == chart["zhi_shi_palace"]
                )
                self.assertEqual(chart["zhi_shi_gate"], envoy["gate"])

    def test_yang_nine_earth_plate_flies_through_center(self):
        chart = self.chart(2011, 6, 18, 3, 56)
        palaces = {item["palace_num"]: item["di_gan"] for item in chart["palaces"]}

        self.assertEqual("阳遁", chart["dun"])
        self.assertEqual("第9局", chart["ju"])
        self.assertEqual(
            {1: "己", 2: "庚", 3: "辛", 4: "壬", 5: "癸",
             6: "丁", 7: "丙", 8: "乙", 9: "戊"},
            palaces,
        )

    def test_real_chart_inputs_cover_second_batch_learning_states(self):
        wonder_chart = self.chart(2026, 9, 1, 2)
        wonder_palaces = {
            item["palace_num"]: item for item in wonder_chart["palaces"]
        }
        self.assertEqual("丙", wonder_palaces[6]["tian_gan"])

        five_not_meet_chart = self.chart(2026, 9, 1, 4)
        self.assertEqual(("戊", "甲"), (
            five_not_meet_chart["ba_zi"]["day"]["stem"],
            five_not_meet_chart["ba_zi"]["hour"]["stem"],
        ))

        punishment_chart = self.chart(2026, 9, 1, 6)
        punishment_palaces = {
            item["palace_num"]: item for item in punishment_chart["palaces"]
        }
        self.assertEqual("戊", punishment_palaces[3]["tian_gan"])

    def test_center_stem_case_is_available_for_kun_lodging_rule(self):
        chart = self.chart(2026, 9, 12, 0)
        palaces = {item["palace_num"]: item for item in chart["palaces"]}

        self.assertEqual("己", palaces[5]["tian_gan"])
        self.assertEqual("己", palaces[2]["lodged_tian_gan"])

    def test_real_chart_inputs_cover_first_stem_response_batch(self):
        morning = self.chart(2026, 1, 1, 8)
        morning_palaces = {item["palace_num"]: item for item in morning["palaces"]}
        self.assertEqual(("戊", "丙"), (
            morning_palaces[2]["tian_gan"], morning_palaces[2]["di_gan"],
        ))
        self.assertEqual(("丙", "庚"), (
            morning_palaces[6]["tian_gan"], morning_palaces[6]["di_gan"],
        ))

        noon = self.chart(2026, 1, 1, 12)
        noon_palaces = {item["palace_num"]: item for item in noon["palaces"]}
        expected_pairs = {
            1: ("癸", "丁"), 3: ("辛", "乙"),
            7: ("乙", "辛"), 9: ("丁", "癸"),
        }
        self.assertEqual(expected_pairs, {
            number: (noon_palaces[number]["tian_gan"], noon_palaces[number]["di_gan"])
            for number in expected_pairs
        })

    def test_lodged_tian_qin_stem_uses_its_rotated_palace_for_response(self):
        chart = self.chart(2026, 1, 5, 2)
        palaces = {item["palace_num"]: item for item in chart["palaces"]}

        self.assertEqual(("辛", "乙"), (
            palaces[1]["lodged_tian_gan"], palaces[1]["di_gan"],
        ))

    def test_birth_dates_provide_full_year_pillars_for_life_stem(self):
        cases = {
            (1984, 7, 1): "甲子",
            (1994, 7, 1): "甲戌",
            (2004, 7, 1): "甲申",
            (2024, 1, 20): "癸卯",
            (2024, 7, 1): "甲辰",
        }
        for (year, month, day), expected in cases.items():
            with self.subTest(date=(year, month, day)):
                chart = self.chart(year, month, day, 12)
                self.assertEqual(expected, (
                    chart["ba_zi"]["year"]["stem"]
                    + chart["ba_zi"]["year"]["branch"]
                ))


if __name__ == "__main__":
    unittest.main()
