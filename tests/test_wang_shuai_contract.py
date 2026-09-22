"""六爻旺衰五态月令表契约测试（DEF-4 修复锁表，2026-09-20）。

背景：`getWangShuai`（src/common/tian_gan/wu_xing_utils.cppm）曾将"相/休"与"囚/死"
两组标签对调（实现与自身 docstring、与《翼氏大典》月令通行表双重矛盾）。
该表在增删卜易系、黄金策系与现代教材间不存在分歧，属纯代码缺陷，不是 D1 流派
决策项；唯一消费方为六爻引擎的爻 wangShuai 字段（并联动暗动判定"须旺或相"，
liu_yao.cppm）。本测试以权威参考表重算并锁定 CLI 输出：

* 五张季节标准表全量：春（寅月）、夏（午月）、四季（辰月）、秋（酉月）、冬（子月），
  每表用乾宫卦六爻（纳甲含水木土火金）覆盖当月全部五态断言；
* 月支守卫：逐案断言引擎返回的月支与所选表一致（防交节边界误取样）；
* 暗动反转：旺/相之爻受日冲才暗动——2025-02-12 壬子日静卦，四爻午火"相"
  且子午冲 → an_dong=True；修复前午被误标"休"则恒为 False，此为口径回正的行为证据；
* 口径自述：rule_profile.wang_shuai 文本必须含"当令者旺"与"DEF-4"修复注记。
"""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "build" / "examples" / "liu_yao_web_cli"

# 《翼氏大典》四时旺相休囚死 + 四季土旺表（增删卜易/现代教材同口径），
# 以"当令五行 → {爻五行: 五态}"登记，本表即测试权威，勿以代码输出回填。
MONTH_TABLES = {
    "木": {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"},  # 春：木旺火相水休金囚土死
    "火": {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"},  # 夏：火旺土相木休水囚金死
    "土": {"土": "旺", "金": "相", "火": "休", "木": "囚", "水": "死"},  # 四季月：土旺金相火休木囚水死
    "金": {"金": "旺", "水": "相", "土": "休", "火": "囚", "木": "死"},  # 秋：金旺水相土休火囚木死
    "水": {"水": "旺", "木": "相", "金": "休", "土": "囚", "火": "死"},  # 冬：水旺木相金休土囚火死
}
# 月支 → 当令五行（辰戌丑未视作土，与内核四季月简化口径一致）
BRANCH_TO_ELEMENT = {
    "寅": "木", "卯": "木", "巳": "火", "午": "火", "申": "金", "酉": "金",
    "亥": "水", "子": "水", "辰": "土", "戌": "土", "丑": "土", "未": "土",
}

# 乾宫卦（hexagram_code 111111）纳甲自下而上：甲子水/甲寅木/甲辰土/壬午火/壬申金/壬戌土，
# 六个地支恰含全部五行，每案可锁该月令表全部五态（土出现两次）。
QIAN_CODE = "111111"
QIAN_ELEMENTS = ["水", "木", "土", "火", "金", "土"]

# 五案：公历日期均在所选月支区间中部，避开交节边界。
# 2025-02-12 为壬子日：子冲四爻午，兼作暗动反转取证日。
CASES = [
    {"label": "春·寅月木令", "date": {"year": 2025, "month": 2, "day": 12, "hour": 10},
     "month_branch": "寅", "element": "木"},
    {"label": "夏·午月火令", "date": {"year": 2025, "month": 6, "day": 20, "hour": 10},
     "month_branch": "午", "element": "火"},
    {"label": "四季·辰月土令", "date": {"year": 2025, "month": 4, "day": 16, "hour": 10},
     "month_branch": "辰", "element": "土"},
    {"label": "秋·酉月金令", "date": {"year": 2025, "month": 9, "day": 20, "hour": 10},
     "month_branch": "酉", "element": "金"},
    {"label": "冬·子月水令", "date": {"year": 2025, "month": 12, "day": 20, "hour": 10},
     "month_branch": "子", "element": "水"},
]


def run_cli(payload: dict) -> dict:
    if not BIN.exists():
        raise unittest.SkipTest(f"二进制未构建: {BIN}")
    completed = subprocess.run([str(BIN)], input=json.dumps(payload),
                               capture_output=True, text=True, timeout=30, cwd=ROOT,
                               check=False)
    if completed.returncode != 0:
        raise AssertionError(f"{BIN.name} 退出码 {completed.returncode}: {completed.stdout[:200]}")
    return json.loads(completed.stdout)


class WangShuaiMonthlyTableTest(unittest.TestCase):
    def test_five_season_tables_locked(self):
        """五张月令表逐爻锁定：每爻 wangShuai 必须等于权威表按当月月令的映射。"""
        for case in CASES:
            with self.subTest(case["label"]):
                out = run_cli({"calendar": "solar", "date": case["date"],
                               "hexagram_code": QIAN_CODE, "changing_lines": []})
                month_branch = out["ba_zi"]["month"]["branch"]
                self.assertEqual(month_branch, case["month_branch"],
                                 f"{case['label']} 取样日已越交节边界，请换日期")
                table = MONTH_TABLES[case["element"]]
                yao = sorted(out["yao"], key=lambda y: y["position"])
                self.assertEqual([y["mainElement"] for y in yao], QIAN_ELEMENTS)
                self.assertEqual([y["wangShuai"] for y in yao],
                                 [table[e] for e in QIAN_ELEMENTS])

    def test_table_self_consistency(self):
        """参考表自校验：五态与生克定义一一对应，防表抄错。"""
        order = ["木", "火", "土", "金", "水"]  # 相生循环；相克为 +2
        idx = {e: i for i, e in enumerate(order)}
        for element in order:
            m = idx[element]
            expected = {element: "旺",
                        order[(m + 1) % 5]: "相",   # 月令生爻
                        order[(m + 4) % 5]: "休",   # 爻生月令
                        order[(m + 3) % 5]: "囚",   # 爻克月令
                        order[(m + 2) % 5]: "死"}   # 月令克爻
            self.assertEqual(MONTH_TABLES[element], expected, f"{element} 令表有误")
        # 与经典口诀逐字对齐（《翼氏大典》四时之序）
        self.assertEqual(MONTH_TABLES["木"], {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"})
        for branch, element in BRANCH_TO_ELEMENT.items():
            self.assertIn(element, MONTH_TABLES)

    def test_an_dong_requires_wang_or_xiang(self):
        """暗动须旺/相之爻被日冲：2025-02-12 壬子日寅月，四爻午火相而受子冲。"""
        out = run_cli({"calendar": "solar", "date": CASES[0]["date"],
                       "hexagram_code": QIAN_CODE, "changing_lines": []})
        yao = {y["position"]: y for y in out["yao"]}
        self.assertEqual(yao[4]["wangShuai"], "相")
        self.assertTrue(yao[4]["an_dong"], "相爻受日冲应暗动（修复前误标休则恒 False）")
        others = [yao[p]["an_dong"] for p in (1, 2, 3, 5, 6)]
        self.assertFalse(any(others), "非旺/相或未受冲之爻不应暗动")

    def test_rule_profile_honest_note(self):
        """口径自述须声明通行表映射与 DEF-4 修复注记。"""
        out = run_cli({"calendar": "solar", "date": CASES[0]["date"],
                       "hexagram_code": QIAN_CODE, "changing_lines": []})
        note = out["meta"]["rule_profile"]["rules"]["wang_shuai"]
        self.assertIn("当令者旺", note)
        self.assertIn("月令生爻者相", note)
        self.assertIn("DEF-4", note)


if __name__ == "__main__":
    unittest.main()
