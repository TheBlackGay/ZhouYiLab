"""DEF-1 回归：逆排大限（阴男/阳女）第 12 限天干越界崩溃。

历史故障：gan_offset=-i 时 C++ 负数取模产生 gan_idx=-1，
get_si_hua_star_names 数组越界 → fortune 直接 CALCULATION_FAILED。
修复为真回绕后，本测试锁定"合法输入不再崩溃 + 十二限齐全"。
注意：大限干支的口径本身（五虎遁 vs 巡运）仍是 D11/DEF-2 复核项，
本测试只锁结构与不崩溃，不锁具体干支值。
"""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIWEI_CLI = ROOT / "build" / "examples" / "zi_wei_web_cli"


def run_cli(payload):
    completed = subprocess.run(
        [str(ZIWEI_CLI)], input=json.dumps(payload),
        capture_output=True, text=True, timeout=30, cwd=ROOT, check=False)
    return completed.returncode, json.loads(completed.stdout)


def birth(year, month, day, hour, gender):
    return {"operation": "chart",
            "birth": {"year": year, "month": month, "day": day, "hour": hour,
                      "minute": 0, "second": 0, "gender": gender},
            "time_correction": {"mode": "standard_time"}}


class ReverseDaXianRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ZIWEI_CLI.exists():
            raise unittest.SkipTest("zi_wei_web_cli 尚未构建")

    def test_yin_male_chart_has_twelve_da_xian_without_crash(self):
        # 2001 辛巳：年支巳 index=5 奇 → 阴 → 男命逆排（曾崩溃）
        code, data = run_cli(birth(2001, 5, 20, 10, "male"))
        self.assertNotIn("error", data, data.get("error"))
        self.assertEqual(code, 0)
        da_xian = data.get("da_xian") or []
        self.assertEqual(len(da_xian), 12, "十二限必须齐全")
        self.assertEqual(sorted(x["gong_index"] for x in da_xian), list(range(12)),
                         "逆排十二限的宫位索引必须是完整排列")
        for item in da_xian:
            self.assertEqual(item["end_age"] - item["start_age"], 9, "每限管十年")

    def test_yang_female_chart_has_twelve_da_xian_without_crash(self):
        # 2002 壬午：年支午 index=6 偶 → 阳 → 女命逆排（同为逆排行程）
        code, data = run_cli(birth(2002, 3, 15, 8, "female"))
        self.assertNotIn("error", data, data.get("error"))
        self.assertEqual(len(data.get("da_xian") or []), 12)
        self.assertEqual(sorted(x["gong_index"] for x in data["da_xian"]), list(range(12)))

    def test_reverse_fortune_layer_works(self):
        """fortune 的 decade 层走同一条 arrange_da_xian 路径。"""
        completed = subprocess.run(
            [str(ZIWEI_CLI)], input=json.dumps({
                "operation": "fortune",
                "birth": {"year": 2001, "month": 5, "day": 20, "hour": 10,
                          "minute": 0, "second": 0, "gender": "male"},
                "time_correction": {"mode": "standard_time"},
                "target": {"year": 2117, "month": 1, "day": 1, "hour": 10,
                           "minute": 0, "second": 0},
                "layers": ["decade"]}),
            capture_output=True, text=True, timeout=30, cwd=ROOT, check=False)
        data = json.loads(completed.stdout)
        self.assertNotIn("error", data, data.get("error"))
        da_xian = data.get("fortune", {}).get("da_xian") or {}
        self.assertEqual(da_xian.get("age_range"), "115-124",
                         "必须命中曾经越界崩溃的逆排第 12 限")
        self.assertEqual(len(da_xian.get("si_hua") or []), 4,
                         "第 12 限四化在回绕修复后必须完整可得")


if __name__ == "__main__":
    unittest.main()
