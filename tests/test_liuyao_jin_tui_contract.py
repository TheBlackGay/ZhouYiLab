"""六爻进退神《增删卜易》口径契约（D1=A 落地锁，2026-09-20）。

《增删卜易》：进神唯子水动化丑土、巳火动化午火；退神唯丑化子、午化巳；
"寅化卯、卯化辰"等他派邻支进神说，本书明言"……非是"。
原实现为八对邻支顺行表（DEF-5 第三项），随 D1=A 收窄为四对。

本测试不依赖记忆硬编码：扫描纯卦×动爻组合，从内核输出取每例
（本爻支, 变爻支）对，断言 jin_shen/tui_shen 标记恰等于四对口径；
同时验证目标对确有出现（防空转），并锁 rule_profile state_tags_scope
已声明新口径。
"""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "build" / "examples" / "liu_yao_web_cli"

# 2025-02-12 寅月（旺衰表由锁表测试另行覆盖）；时辰不进入退判定
DATE = {"calendar": "solar", "date": {"year": 2025, "month": 2, "day": 12, "hour": 10}}

JIN_PAIRS = {("子", "丑"), ("巳", "午")}
TUI_PAIRS = {("丑", "子"), ("午", "巳")}
# 曾经八对邻支表误判的对照例（必须出现在扫描集内才有鉴别力）
REJECTED = {("寅", "卯"), ("卯", "辰"), ("申", "酉"), ("亥", "子")}

# 乾兑离震巽坎艮坤（自下而上卦码六位拼接）
PURE_CODES = ["111111", "110110", "101101", "100100",
              "011011", "010010", "001001", "000000"]
SIX_RELATIVE_FAMILIES = ["111001", "001000", "110010", "100111",
                         "010110", "101000", "011101", "000111"]


def run(payload: dict) -> dict:
    completed = subprocess.run([str(BIN)], input=json.dumps(payload),
                               capture_output=True, text=True, timeout=30, cwd=ROOT,
                               check=False)
    assert completed.returncode == 0, completed.stdout[:200]
    return json.loads(completed.stdout)


class JinTuiShenContractTests(unittest.TestCase):
    def sweep(self):
        if not BIN.exists():
            self.skipTest("liu_yao_web_cli 未构建")
        seen = []
        for code in PURE_CODES + SIX_RELATIVE_FAMILIES:
            for moving in range(1, 7):
                plate = run({**DATE, "hexagram_code": code, "changing_lines": [moving]})
                yao = next(y for y in plate["yao"] if y["position"] == moving)
                branch = yao["mainPillar"]["branch"]
                changed = (yao.get("changedPillar") or {}).get("branch")
                if not changed:
                    continue
                seen.append((code, moving, branch, changed,
                             bool(yao.get("jin_shen")), bool(yao.get("tui_shen"))))
        return seen

    def test_flags_exactly_match_zenshan_four_pairs(self):
        seen = self.sweep()
        self.assertGreater(len(seen), 30, "扫描样本过少，测试可能空转")
        for code, moving, b, c, jin, tui in seen:
            with self.subTest(pair=f"{b}->{c}", code=code, moving=moving):
                self.assertEqual(jin, (b, c) in JIN_PAIRS)
                self.assertEqual(tui, (b, c) in TUI_PAIRS)
        observed = {(b, c) for _, _, b, c, _, _ in seen}
        self.assertTrue(observed & (JIN_PAIRS | TUI_PAIRS), "四对正反例未出现在扫描集中")
        self.assertTrue(observed & REJECTED, "旧邻支误判对照例未出现，缺鉴别力")

    def test_rule_profile_declares_zenshan_caliber(self):
        if not BIN.exists():
            self.skipTest("liu_yao_web_cli 未构建")
        plate = run({**DATE, "hexagram_code": "111111", "changing_lines": [1]})
        profile = plate["meta"]["rule_profile"]
        self.assertEqual(profile["profile_version"], "liu-yao-rules/0.2")
        note = profile["rules"]["state_tags_scope"]
        self.assertIn("增删卜易", note)
        self.assertIn("子化丑", note)
        self.assertIn("废弃", note)


if __name__ == "__main__":
    unittest.main()
