"""梅花易数事实盘契约（meihua-plate/1.0，M1 内核+CLI）。

覆盖（全部 CLI 参数化，二进制未构建时跳过）：
* 书例锁：《梅花易数》卷首"辰年十二月十七日申时"——取丙辰年 1916 农历腊月十七
  （避开 1976 版会踩立春换年的边界）复现：泽火革初爻动，互天风姤、变泽山咸；
  体=上卦兑金得丑月之相、用=下卦离火处休（月令表与六爻 DEF-4 修复后共用，
  本模块为该函数六爻之外的第一实战消费方）；
* 闰月十五分界（D13.1）：2023 闰二月十日作本月、二十日作下月，含"余0作满数"路径
  （坤为地六爻动/离为火五爻动变天火同人的卦码全锁）；
* 报数起卦（D13.3）：两数 [3,7] → 火山旅四爻动（体艮土、用离火、用生体；
  互泽风大过、变艮为山）；三数动爻含 (sum)%6==0→6 路径；
* 公历转农历取数与书例同盘；
* 脏输入守卫：mode/calendar 非法、报数个数与正负、日期越界；
* 口径标识：meihua-rules/0.1 + calibration_status=pending + 十五分界/DEF-4 表注记；
* 断语边界：M1 事实盘不出现吉凶/应期/断语类字段。
"""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "build" / "examples" / "mei_hua_web_cli"


def run_cli(payload: dict):
    if not BIN.exists():
        raise unittest.SkipTest(f"二进制未构建: {BIN}")
    completed = subprocess.run([str(BIN)], input=json.dumps(payload),
                               capture_output=True, text=True, timeout=30, cwd=ROOT,
                               check=False)
    try:
        out = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"输出非 JSON: {completed.stdout[:200]} / {completed.stderr[:200]}")
    return completed.returncode, out


def ok(payload: dict) -> dict:
    code, out = run_cli(payload)
    assert code == 0 and "error" not in out, out
    return out


class MeiHuaPlateTests(unittest.TestCase):
    def test_book_example_chen_year_ge_gua(self):
        """丙辰年腊十七申时（取 1916 不踩立春边界）：泽火革初爻动、互天风姤、变泽山咸。"""
        out = ok({"mode": "time", "calendar": "lunar",
                  "date": {"year": 1916, "month": 12, "day": 17, "hour": 16}})
        self.assertEqual(out["schema_version"], "meihua-plate/1.0")
        casting = out["casting"]
        self.assertEqual(
            (casting["year_branch_order"], casting["lunar_month_used"],
             casting["lunar_day"], casting["hour_branch_order"]), (5, 12, 17, 9))
        self.assertEqual((casting["upper_sum"], casting["lower_sum"]), (34, 43))
        self.assertEqual(out["moving_line"], 1)
        self.assertEqual(out["ba_zi"]["year"]["stem"] + out["ba_zi"]["year"]["branch"], "丙辰")
        self.assertEqual(out["ba_zi"]["month_command"], "丑")
        self.assertEqual(out["trigrams"]["upper"], {"number": 2, "name": "兑", "element": "金"})
        self.assertEqual(out["trigrams"]["lower"], {"number": 3, "name": "离", "element": "火"})
        self.assertEqual(out["ben_gua"]["name"], "泽火革")
        self.assertEqual(out["hu_gua"]["name"], "天风姤")
        self.assertEqual(out["bian_gua"]["name"], "泽山咸")
        self.assertEqual(out["ben_gua"]["code"], "101110")
        self.assertEqual(out["hu_gua"]["code"], "011111")
        self.assertEqual(out["bian_gua"]["code"], "001110")
        ti_yong = out["ti_yong"]
        self.assertEqual((ti_yong["ti"], ti_yong["yong"]), ("upper", "lower"))
        self.assertEqual(ti_yong["relation"], "用克体")
        self.assertEqual(ti_yong["ti_wang_shuai"], "相")
        self.assertEqual(ti_yong["yong_wang_shuai"], "休")

    def test_leap_month_fifteen_boundary(self):
        """2023 闰二月：10 日作本月（2），20 日作下月（3）——D13.1 与紫微 D12 同尺。"""
        a = ok({"mode": "time", "calendar": "lunar",
                "date": {"year": 2023, "month": 2, "day": 10, "hour": 14,
                         "leap_month": True}})
        ca = a["casting"]
        self.assertEqual(ca["lunar_month_input_signed"], -2)
        self.assertEqual(ca["lunar_month_used"], 2)
        self.assertEqual(ca["leap_month_rule"], "fifteen_boundary")
        # 卯4+2+10=16 → 上坤8（余0作满）；+未8=24 → 下坤8；动 24%6=0 → 六爻
        self.assertEqual((ca["upper_sum"], ca["lower_sum"]), (16, 24))
        self.assertEqual((a["trigrams"]["upper"]["number"],
                          a["trigrams"]["lower"]["number"], a["moving_line"]), (8, 8, 6))
        self.assertEqual(a["ben_gua"]["name"], "坤为地")
        self.assertEqual(a["bian_gua"]["name"], "山地剥")
        self.assertEqual(a["ti_yong"]["relation"], "体用比和")
        b = ok({"mode": "time", "calendar": "lunar",
                "date": {"year": 2023, "month": 2, "day": 20, "hour": 14,
                         "leap_month": True}})
        self.assertEqual(b["casting"]["lunar_month_used"], 3)
        # 卯4+3+20=27 → 上离3；+8=35 → 下离3；35%6=5 动五爻
        self.assertEqual((b["trigrams"]["upper"]["number"],
                          b["trigrams"]["lower"]["number"], b["moving_line"]), (3, 3, 5))
        self.assertEqual(b["ben_gua"]["name"], "离为火")
        self.assertEqual(b["bian_gua"]["name"], "天火同人")

    def test_numbers_mode_two_and_three(self):
        """报数 [3,7]：火山旅四爻动、用生体（寅月：体艮土死、用离火相）；互大过、变艮为山。"""
        out = ok({"mode": "numbers", "calendar": "solar",
                  "date": {"year": 2025, "month": 2, "day": 12, "hour": 10},
                  "numbers": [3, 7]})
        self.assertEqual(out["casting"]["method"], "numbers")
        self.assertEqual(out["casting"]["reported"], [3, 7])
        self.assertEqual(out["ben_gua"]["name"], "火山旅")
        self.assertEqual(out["ben_gua"]["code"], "001101")
        self.assertEqual(out["hu_gua"]["code"], "011110")
        self.assertEqual(out["bian_gua"]["code"], "001001")
        self.assertEqual(out["moving_line"], 4)
        self.assertEqual(out["ti_yong"]["relation"], "用生体")
        self.assertEqual(out["ti_yong"]["ti_wang_shuai"], "死")
        self.assertEqual(out["ti_yong"]["yong_wang_shuai"], "相")
        # 三数：12%6=0 → 动爻作 6
        three = ok({"mode": "numbers", "calendar": "solar",
                    "date": {"year": 2025, "month": 2, "day": 12, "hour": 10},
                    "numbers": [3, 7, 2]})
        self.assertEqual(three["moving_line"], 6)
        self.assertEqual(three["ben_gua"]["code"], "001101")  # 上下卦不变

    def test_solar_mode_lunar_conversion(self):
        """公历输入经历法层转农历取数：1917-01-10 16 时即书例同一盘。"""
        solar = ok({"mode": "time", "calendar": "solar",
                    "date": {"year": 1917, "month": 1, "day": 10, "hour": 16}})
        self.assertEqual(solar["casting"]["lunar_month_used"], 12)
        self.assertEqual(solar["casting"]["lunar_day"], 17)
        self.assertEqual(solar["ben_gua"]["name"], "泽火革")
        self.assertEqual(solar["moving_line"], 1)

    def test_guards(self):
        for payload in (
            {"mode": "other", "date": {"year": 2025, "month": 2, "day": 12, "hour": 10}},
            {"calendar": "mingong", "date": {"year": 2025, "month": 2, "day": 12, "hour": 10}},
            {"mode": "numbers", "date": {"year": 2025, "month": 2, "day": 12, "hour": 10},
             "numbers": [3]},
            {"mode": "numbers", "date": {"year": 2025, "month": 2, "day": 12, "hour": 10},
             "numbers": [3, 0]},
            {"mode": "numbers", "date": {"year": 2025, "month": 2, "day": 12, "hour": 10},
             "numbers": [3, 7, 2, 1]},
            {"date": {"year": 2025, "month": 13, "day": 1, "hour": 10}},
        ):
            with self.subTest(payload=payload):
                code, out = run_cli(payload)
                self.assertNotEqual(code, 0, payload)
                self.assertIn("error", out, payload)

    def test_rule_profile_registered(self):
        out = ok({"date": {"year": 2025, "month": 2, "day": 12, "hour": 10}})
        profile = out["meta"]["rule_profile"]
        self.assertEqual(profile["profile_version"], "meihua-rules/0.1")
        self.assertEqual(profile["calibration_status"], "pending")
        blob = json.dumps(profile, ensure_ascii=False)
        self.assertIn("十五", profile["rules"]["leap_month_rule"])
        self.assertIn("DEF-4", profile["rules"]["wang_shuai_basis"])
        self.assertIn("立春", blob)
        for value in profile["rules"].values():
            self.assertTrue(any("\u4e00" <= ch <= "\u9fff" for ch in value))

    def test_fact_layer_has_no_judgment_fields(self):
        """M1 事实盘边界：断语类词只查事实层（meta 的口径自述允许出现"吉凶"字样）。"""
        out = ok({"calendar": "lunar",
                  "date": {"year": 1916, "month": 12, "day": 17, "hour": 16}})
        blob = json.dumps({k: v for k, v in out.items() if k != "meta"}, ensure_ascii=False)
        for word in ("吉", "凶", "应期", "断语"):
            self.assertNotIn(word, blob)


if __name__ == "__main__":
    unittest.main()
