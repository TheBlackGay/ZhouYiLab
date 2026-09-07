import json
import re
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTML = (PROJECT_ROOT / "web" / "bazi.html").read_text(encoding="utf-8")
JAVASCRIPT = (PROJECT_ROOT / "web" / "bazi.js").read_text(encoding="utf-8")
SHEN_SHA_CPP = (PROJECT_ROOT / "src" / "ba_zi" / "ba_zi_shen_sha.cppm").read_text(encoding="utf-8")
SERVER = (PROJECT_ROOT / "web" / "server.py").read_text(encoding="utf-8")
CMAKE = (PROJECT_ROOT / "examples" / "CMakeLists.txt").read_text(encoding="utf-8")
BAZI_CLI = PROJECT_ROOT / "build" / "examples" / "ba_zi_web_cli"
LU_SHEN_PATH = PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "lu_shen.json"
LU_SHEN = json.loads(LU_SHEN_PATH.read_text(encoding="utf-8"))
JIN_YU_PATH = PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "jin_yu.json"
JIN_YU = json.loads(JIN_YU_PATH.read_text(encoding="utf-8"))
YANG_REN = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "yang_ren.json").read_text(encoding="utf-8"))
SHI_E_DA_BAI = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "shi_e_da_bai.json").read_text(encoding="utf-8"))
TIAN_YI = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "tian_yi_gui_ren.json").read_text(encoding="utf-8"))
YI_MA = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "yi_ma.json").read_text(encoding="utf-8"))
TIAN_YUE_DE = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "tian_yue_de.json").read_text(encoding="utf-8"))
LIU_E = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "liu_e.json").read_text(encoding="utf-8"))
ZAI_SHA = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "zai_sha.json").read_text(encoding="utf-8"))
AN_JIN = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "an_jin_de_sha.json").read_text(encoding="utf-8"))
GOU_JIAO = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "gou_jiao_sha.json").read_text(encoding="utf-8"))
GU_GUA = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "gu_chen_gua_su.json").read_text(encoding="utf-8"))
JIE_WANG = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "jie_sha_wang_shen.json").read_text(encoding="utf-8"))
JIE_16 = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "jie_sha_shi_liu_ban.json").read_text(encoding="utf-8"))
WANG_16 = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "wang_shen_shi_liu_ban.json").read_text(encoding="utf-8"))
GAN_ZHI_ZA = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "gan_zhi_zi_za_fan.json").read_text(encoding="utf-8"))
OTHER_GROUPS = json.loads((PROJECT_ROOT / "config" / "bazi" / "shen_sha" / "其他神煞分组审计.json").read_text(encoding="utf-8"))


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
        self.assertIn("branch_relations", JAVASCRIPT)
        self.assertIn("interchanges", JAVASCRIPT)
        self.assertIn('id="shen-sha-note"', HTML)
        self.assertIn('id="shen-sha-dialog"', HTML)
        self.assertIn('data-shen-sha-id', JAVASCRIPT)
        self.assertIn('/api/v1/bazi/shen-sha/', JAVASCRIPT)
        self.assertIn("'金舆': 'jin_yu'", JAVASCRIPT)

    def test_server_and_build_register_bazi_cli(self):
        self.assertIn('BAZI_CLI_PATH', SERVER)
        self.assertIn('parsed.path == "/api/v1/bazi/charts"', SERVER)
        self.assertIn('"bazi_cli_available"', SERVER)
        self.assertIn("ba_zi_web_cli", CMAKE)
        self.assertIn('BAZI_SHEN_SHA_ROOT', SERVER)
        self.assertIn('/api/v1/bazi/shen-sha/', SERVER)

    def test_jin_yu_knowledge_base_and_day_stem_rule(self):
        self.assertEqual("calibrated", JIN_YU["calibration_status"])
        self.assertEqual("《三命通会·论金舆》", JIN_YU["source"])
        self.assertEqual("日柱", JIN_YU["calculation"]["priority"][0])
        self.assertEqual("时柱", JIN_YU["calculation"]["priority"][1])
        self.assertEqual("辰", JIN_YU["calculation"]["jin_yu_positions"]["甲"])
        self.assertEqual("未", JIN_YU["calculation"]["jin_yu_positions"]["戊"])
        self.assertEqual("寅", JIN_YU["calculation"]["jin_yu_positions"]["癸"])
        self.assertIn("day_stem", SHEN_SHA_CPP)
        self.assertNotIn("stem_matches_branch(year_stem, branch, jin_yu)", SHEN_SHA_CPP)

    def test_lu_shen_knowledge_base_is_complete(self):
        self.assertEqual("calibrated", LU_SHEN["calibration_status"])
        self.assertIn("《渊海子平》", LU_SHEN["source"])
        self.assertEqual(
            {"甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
             "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子"},
            LU_SHEN["calculation"]["fixed_positions"],
        )
        self.assertEqual({"甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"}, set(LU_SHEN["variants"]))
        self.assertTrue(all(len(items) == 5 for items in LU_SHEN["variants"].values()))
        self.assertEqual(50, sum(len(items) for items in LU_SHEN["variants"].values()))
        self.assertEqual("卯禄", next(item for item in LU_SHEN["variants"]["癸"] if item["ganzhi"] == "庚子")["name"])

    def test_yang_ren_and_shi_e_tables(self):
        self.assertEqual("calibrated", YANG_REN["calibration_status"])
        self.assertEqual("calibrated", SHI_E_DA_BAI["calibration_status"])
        self.assertEqual({"甲": "卯", "乙": "辰", "丙": "午", "丁": "未", "戊": "午", "己": "未", "庚": "酉", "辛": "戌", "壬": "子", "癸": "丑"}, YANG_REN["positions_by_day_stem"])
        self.assertEqual(["甲辰", "乙巳", "丙申", "丁亥", "戊戌", "己丑", "庚辰", "辛巳", "壬申", "癸亥"], SHI_E_DA_BAI["days"])

    def test_tian_yi_and_yi_ma_calibration(self):
        self.assertEqual("calibrated", TIAN_YI["calibration_status"])
        self.assertEqual("calibrated", YI_MA["calibration_status"])
        self.assertEqual(["丑", "未"], TIAN_YI["calculation"]["common_method"]["甲"])
        self.assertEqual(["丑", "未"], TIAN_YI["calculation"]["guang_lu_method"]["庚"])
        self.assertEqual(["寅", "午"], TIAN_YI["calculation"]["common_method"]["庚"])
        self.assertEqual("申", YI_MA["calculation"]["positions"]["寅午戌"])
        self.assertIn("年支和日支", YI_MA["calculation"]["basis"])

    def test_tian_yue_de_four_independent_fields(self):
        self.assertEqual("calibrated", TIAN_YUE_DE["calibration_status"])
        self.assertEqual(["tiande", "yuede"], TIAN_YUE_DE["calculation"]["main"])
        self.assertEqual(["tiandehe", "yuedehe"], TIAN_YUE_DE["calculation"]["he"])

    def test_liu_e_and_zai_sha_tables(self):
        self.assertEqual("calibrated", LIU_E["calibration_status"])
        self.assertEqual("calibrated", ZAI_SHA["calibration_status"])
        self.assertEqual("卯", LIU_E["calculation"]["positions_by_triple_harmony"]["申子辰"])
        self.assertEqual("午", ZAI_SHA["calculation"]["positions_by_triple_harmony"]["申子辰"])

    def test_an_jin_gou_jiao_and_gu_gua_calibration(self):
        self.assertEqual("calibrated", AN_JIN["calibration_status"])
        self.assertEqual("calibrated", GOU_JIAO["calibration_status"])
        self.assertEqual("calibrated", GU_GUA["calibration_status"])
        self.assertEqual(["yinshen", "posui", "baiyi"], AN_JIN["calculation"]["sub_tags"])
        self.assertEqual(["goushen", "jiaoshen"], GOU_JIAO["calculation"]["main"])

    def test_jie_wang_base_and_reference_boundaries(self):
        self.assertEqual("calibrated", JIE_WANG["calibration_status"])
        self.assertEqual("reference", JIE_16["calibration_status"])
        self.assertEqual("reference", WANG_16["calibration_status"])
        self.assertEqual(["jiesha", "wangshen"], JIE_WANG["calculation"]["base_outputs"])
        self.assertIn("不参与", JIE_WANG["calculation"]["shiliuban"])

    def test_gan_zhi_za_fan_is_reference_only(self):
        self.assertEqual("reference", GAN_ZHI_ZA["calibration_status"])
        self.assertEqual([], GAN_ZHI_ZA["calculation"]["main"])
        self.assertIn("悬针", GAN_ZHI_ZA["calculation"]["sub_tags"])

    def test_other_shen_sha_group_audit_boundaries(self):
        self.assertEqual("pending_implementation", OTHER_GROUPS["groups"]["group1"]["status"])
        self.assertEqual("pending_implementation", OTHER_GROUPS["groups"]["group2"]["status"])
        self.assertEqual("pending_implementation", OTHER_GROUPS["groups"]["group4"]["status"])
        self.assertEqual("reference", OTHER_GROUPS["groups"]["group3"]["status"])
        self.assertEqual("reference", OTHER_GROUPS["groups"]["group5"]["status"])

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
            "day": ["太极贵人", "德秀贵人", "红艳煞", "童子煞"],
            "hour": ["文昌贵人", "天厨贵人", "天德贵人", "月德合", "禄神", "流霞"],
        }
        for key, names in expected_shen_sha.items():
            self.assertTrue(set(names).issubset(set(result["pillars"][key]["shen_sha"])))

        self.assertTrue(all(item["name"] != "禄神" for item in result["pillars"]["year"]["shen_sha_details"]))
        lu_details = [item for item in result["pillars"]["hour"]["shen_sha_details"] if item["id"] == "lu_shen"]
        self.assertEqual([{
            "id": "lu_shen",
            "name": "禄神",
            "position": "归禄",
            "ganzhi": "丁巳",
            "variant": "旺库禄",
            "nature": "吉",
        }], lu_details)

        summary = result["shen_sha_summary"]
        self.assertEqual(["戊"], summary["de_xiu"]["de_stems"])
        self.assertEqual(["甲", "丙"], summary["de_xiu"]["xiu_stems"])
        self.assertTrue(summary["de_xiu"]["matched"])
        self.assertTrue(summary["tong_zi"]["month_rule"])
        self.assertFalse(summary["tong_zi"]["na_yin_rule"])
        self.assertFalse(summary["tong_zi"]["is_double"])
        self.assertFalse(summary["tian_luo_di_wang"]["tian_luo"])
        self.assertFalse(summary["tian_luo_di_wang"]["di_wang"])
        self.assertEqual({
            "matched": True,
            "basis": "日干定禄，遍查年、月、日、时四支",
            "day_stem": "戊",
            "occurrence_count": 1,
        }, summary["lu_shen"])
        self.assertEqual({
            "matched": False,
            "basis": "日干取禄，禄神地支顺推二辰",
            "day_stem": "戊",
            "occurrence_count": 0,
        }, summary["jin_yu"])
        self.assertEqual({"branch_relations", "stem_relations", "interchanges", "sanhe_ju", "wangshuai_info"}, set(summary["relations"]))
        self.assertIsNone(summary["relations"]["wangshuai_info"])
        self.assertTrue(all(item["type"] not in {"zhandou", "fujiang"} for item in summary["relations"]["branch_relations"]))
        self.assertIn("gejiao", summary["auxiliary"])
        self.assertIn("yi_ma", summary)
        self.assertIn("tian_yi_gui_ren", summary)
        self.assertIn("san_qi", summary)
        self.assertEqual({"tiande", "yuede", "tiandehe", "yuedehe"}, set(summary["tian_yue_de"]))
        self.assertFalse(summary["san_qi"]["matched"])

        self.assertEqual(9, result["da_yun"]["start_detail"]["years"])
        self.assertEqual("2004年7月10日 01:24:00", result["da_yun"]["start_detail"]["start_time"])


if __name__ == "__main__":
    unittest.main()
