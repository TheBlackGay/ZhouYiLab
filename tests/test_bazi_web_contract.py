import json
import re
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTML = (PROJECT_ROOT / "web" / "bazi.html").read_text(encoding="utf-8")
JAVASCRIPT = (PROJECT_ROOT / "web" / "bazi.js").read_text(encoding="utf-8")
SERVER = (PROJECT_ROOT / "web" / "server.py").read_text(encoding="utf-8")
CMAKE = (PROJECT_ROOT / "examples" / "CMakeLists.txt").read_text(encoding="utf-8")
BAZI_CLI = PROJECT_ROOT / "build" / "examples" / "ba_zi_web_cli"


class BaZiWebContractTests(unittest.TestCase):
    def test_input_and_result_views_are_available(self):
        calendar_values = set(re.findall(r'name="calendar" value="([^"]+)"', HTML))
        gender_values = set(re.findall(r'name="gender" value="([^"]+)"', HTML))
        self.assertEqual({"solar", "lunar"}, calendar_values)
        self.assertEqual({"male", "female"}, gender_values)
        self.assertIn('id="leap-month"', HTML)
        self.assertIn('id="true-solar"', HTML)
        self.assertIn('id="longitude"', HTML)
        self.assertIn('id="meridian"', HTML)
        self.assertIn('id="dst"', HTML)
        self.assertIn('id="pillar-board"', HTML)
        self.assertIn('id="fortune-list"', HTML)
        self.assertIn('id="chart-tab"', HTML)
        self.assertIn('id="fortune-tab"', HTML)

    def test_frontend_uses_bazi_api_and_renders_core_facts(self):
        self.assertIn("/api/v1/bazi/charts", JAVASCRIPT)
        self.assertIn("hidden_stems", JAVASCRIPT)
        self.assertIn("stem_ten_god", JAVASCRIPT)
        self.assertIn("xun_kong", JAVASCRIPT)
        self.assertIn("da_yun.list", JAVASCRIPT)
        self.assertIn("true_solar_time", JAVASCRIPT)
        self.assertIn("time_correction", JAVASCRIPT)
        self.assertIn("crossed_date_boundary", JAVASCRIPT)
        self.assertIn("star_fortune", JAVASCRIPT)
        self.assertIn("self_sitting", JAVASCRIPT)
        self.assertIn("void_branches", JAVASCRIPT)
        self.assertIn("na_yin", JAVASCRIPT)
        self.assertIn("start_detail", JAVASCRIPT)
        self.assertIn("shen_sha", JAVASCRIPT)
        self.assertIn("shen_sha_summary", JAVASCRIPT)
        self.assertIn('id="shen-sha-note"', HTML)

    def test_server_and_build_register_bazi_cli(self):
        self.assertIn('BAZI_CLI_PATH', SERVER)
        self.assertIn('parsed.path == "/api/v1/bazi/charts"', SERVER)
        self.assertIn('"bazi_cli_available"', SERVER)
        self.assertIn("ba_zi_web_cli", CMAKE)

    @unittest.skipUnless(BAZI_CLI.exists(), "ba_zi_web_cli has not been built")
    def test_calibrated_reference_chart(self):
        request = {
            "calendar": "solar",
            "gender": "male",
            "date": {"year": 1994, "month": 12, "day": 8, "hour": 9, "minute": 5},
            "time_correction": {
                "mode": "true_solar_time",
                "longitude": 120.3,
                "standard_meridian": 120.0,
                "daylight_saving_minutes": 0,
            },
        }
        completed = subprocess.run(
            [str(BAZI_CLI)],
            input=json.dumps(request),
            text=True,
            capture_output=True,
            check=True,
        )
        result = json.loads(completed.stdout)

        self.assertEqual("1994-12-08 09:14:14", result["birth_time"]["chart_time"])
        self.assertEqual(554, result["birth_time"]["total_offset_seconds"])
        expected = {
            "year": ("甲", "戌", "墓", "养", ["申", "酉"], "山头火"),
            "month": ("丙", "子", "胎", "胎", ["申", "酉"], "涧下水"),
            "day": ("戊", "辰", "冠带", "冠带", ["戌", "亥"], "大林木"),
            "hour": ("丁", "巳", "临官", "帝旺", ["子", "丑"], "沙中土"),
        }
        for key, values in expected.items():
            pillar = result["pillars"][key]
            actual = (
                pillar["stem"], pillar["branch"], pillar["star_fortune"],
                pillar["self_sitting"], pillar["void_branches"], pillar["na_yin"],
            )
            self.assertEqual(values, actual)

        expected_shen_sha = {
            "year": ["国印贵人", "太极贵人", "德秀贵人", "空亡"],
            "month": ["太极贵人", "福星贵人", "德秀贵人", "飞刃", "灾煞", "丧门", "将星"],
            "day": ["太极贵人", "德秀贵人", "红艳煞", "童子煞", "金舆"],
            "hour": ["文昌贵人", "天厨贵人", "天德贵人", "月德合", "禄神", "流霞"],
        }
        for key, names in expected_shen_sha.items():
            self.assertEqual(names, result["pillars"][key]["shen_sha"])

        summary = result["shen_sha_summary"]
        self.assertEqual(["戊"], summary["de_xiu"]["de_stems"])
        self.assertEqual(["甲", "丙"], summary["de_xiu"]["xiu_stems"])
        self.assertTrue(summary["de_xiu"]["matched"])
        self.assertTrue(summary["tong_zi"]["month_rule"])
        self.assertFalse(summary["tong_zi"]["na_yin_rule"])
        self.assertFalse(summary["tong_zi"]["is_double"])
        self.assertFalse(summary["tian_luo_di_wang"]["tian_luo"])
        self.assertFalse(summary["tian_luo_di_wang"]["di_wang"])

        self.assertEqual(9, result["da_yun"]["start_detail"]["years"])
        self.assertEqual("2004年7月10日 01:24:00", result["da_yun"]["start_detail"]["start_time"])


if __name__ == "__main__":
    unittest.main()
