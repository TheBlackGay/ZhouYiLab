"""大六壬 2.0.0 I1：引擎契约测试（DLR-205）。

覆盖：
* meta.rule_profile 口径标识为纯新增，既有字段语义零变化；
* 历法/闰月入参行为（含不存在闰月的可定位错误码）；
* profile_version 与 calibration_status 的锁定（防止口径静默漂移）。
"""
import json
import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DLR_CLI = PROJECT_ROOT / "build" / "examples" / "da_liu_ren_web_cli"

LEGACY_TOP_LEVEL = {
    "ba_zi", "yue_jiang", "gui_ren", "is_day",
    "si_ke", "san_chuan", "tian_di_pan", "shen_sha", "gua_ti",
}
RULE_PROFILE_KEYS = {
    "four_pillars", "time_granularity", "yue_jiang", "gui_ren", "shen_jiang",
    "gan_ji_gong", "san_chuan", "dun_gan", "liu_qin", "gua_ti",
}


def run_cli(payload):
    completed = subprocess.run(
        [str(DLR_CLI)], input=json.dumps(payload),
        capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT, check=False)
    return completed.returncode, json.loads(completed.stdout)


class DaLiuRenEngineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DLR_CLI.exists():
            raise unittest.SkipTest("da_liu_ren_web_cli 尚未构建")

    def test_rule_profile_is_additive_and_complete(self):
        code, data = run_cli({"calendar": "solar",
                              "date": {"year": 2024, "month": 10, "day": 13, "hour": 14}})
        self.assertEqual(code, 0)
        self.assertTrue(LEGACY_TOP_LEVEL.issubset(data), "既有字段不得消失")
        profile = data["meta"]["rule_profile"]
        self.assertEqual(profile["profile_version"], "da-liu-ren-rules/0.2")
        self.assertEqual(data["meta"]["yuejiang_method"], "zhongqi", "默认必须为中气过宫（D2）")
        self.assertEqual(profile["calibration_status"], "pending",
                         "大六壬算法未校准前不得伪装已校准")
        self.assertEqual(set(profile["rules"]), RULE_PROFILE_KEYS)
        for text in profile["rules"].values():
            self.assertTrue(isinstance(text, str) and text.strip())
        # 天地盘 12 位、三传 stage 顺序等旧契约不受影响
        self.assertEqual(len(data["tian_di_pan"]), 12)
        self.assertEqual([x["stage"] for x in data["san_chuan"]["details"]],
                         ["chu_chuan", "zhong_chuan", "mo_chuan"])

    def test_lunar_leap_month_accepted_and_rejected(self):
        ok_code, ok = run_cli({"calendar": "lunar", "date": {
            "year": 2025, "month": 6, "day": 10, "hour": 10, "leap_month": True}})
        self.assertEqual(ok_code, 0, ok)
        self.assertNotIn("error", ok)
        bad_code, bad = run_cli({"calendar": "lunar", "date": {
            "year": 2024, "month": 4, "day": 1, "hour": 10, "leap_month": True}})
        self.assertEqual(bad_code, 1)
        self.assertEqual(bad["error"]["code"], "INVALID_ARGUMENT")

    def test_yuejiang_method_boundary(self):
        """D2：2025-02-18 05:00——古法定切已换亥、中气交节(12:13)未到仍子。"""
        date = {"year": 2025, "month": 2, "day": 18, "hour": 5}
        _, zh = run_cli({"calendar": "solar", "date": date})
        self.assertEqual(zh["yue_jiang"], "子")
        _, gf = run_cli({"calendar": "solar", "date": date, "yuejiang_method": "guifa_suicha"})
        self.assertEqual(gf["meta"]["yuejiang_method"], "guifa_suicha")
        self.assertEqual(gf["yue_jiang"], "亥")
        code, bad = run_cli({"calendar": "solar", "date": date, "yuejiang_method": "bogus"})
        self.assertEqual((code, bad["error"]["code"]), (1, "INVALID_ARGUMENT"))

    def test_invalid_calendar_reports_invalid_argument(self):
        code, data = run_cli({"calendar": "venus",
                              "date": {"year": 2024, "month": 10, "day": 13, "hour": 14}})
        self.assertEqual(code, 1)
        self.assertEqual(data["error"]["code"], "INVALID_ARGUMENT")


if __name__ == "__main__":
    unittest.main()
