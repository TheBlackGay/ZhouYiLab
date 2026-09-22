"""六爻 64 卦排列表全量契约锁（DEF-7 修复回归网，2026-09-21）。

2026-09-20 D1=A 验收时发现：hexagramMap 中 6 条（地水师/天雷无妄/
风水涣/天水讼/天火同人/雷泽归妹）的 innerHexagram/outerHexagram
与自身卦码上下互反，导致这些卦的本卦与变卦纳甲全错
（典型征象：乾卦二爻动变天火同人，变爻地支显示 寅→寅，应为 寅→丑）。

本测试三方互证锁死全表：
1. 卦码 ↔ 卦名上下卦 ↔ inner/outer 元数据 必须一致（64/64）；
2. 结构规律：本宫卦 内卦=外卦=宫卦；归魂卦 内卦=宫卦；
3. 引擎实算抽验：师/同人 本卦纳支、乾动二爻 变爻纳支（修复前后行为不同）。
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "liu_yao" / "liu_yao.cppm"
BIN = ROOT / "build" / "examples" / "liu_yao_web_cli"

DATE = {"calendar": "solar", "date": {"year": 2025, "month": 2, "day": 12, "hour": 10}}

# 卦自下而上六位（索引0=初爻）→ 三爻卦码
TRI = {"111": "乾", "110": "兑", "101": "离", "100": "震",
       "011": "巽", "010": "坎", "001": "艮", "000": "坤"}
# 卦名前两位=上卦自然象、下卦自然象（纯卦"X为Y"特判）
NAME2TRI = {"天": "乾", "泽": "兑", "火": "离", "雷": "震",
            "风": "巽", "水": "坎", "山": "艮", "地": "坤"}

ENTRY_PAT = re.compile(
    r'\{"([01]{6})",\s*\{"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",'
    r'\s*(\d+),\s*(\d+),\s*(?:true|false),\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\}\}')


def load_entries():
    text = SRC.read_text(encoding="utf-8")
    block = re.search(r'hexagramMap\s*=\s*\{(.*?)\n\};', text, re.S)
    assert block, "hexagramMap 块未找到（源结构变更请同步本测试）"
    return ENTRY_PAT.findall(block.group(1))


def name_trigrams(name):
    """返回 (下卦, 上卦)。"""
    if "为" in name:
        t = NAME2TRI[name.split("为")[1][0]]
        return t, t
    return NAME2TRI[name[1]], NAME2TRI[name[0]]


def run(payload: dict) -> dict:
    completed = subprocess.run([str(BIN)], input=json.dumps(payload),
                               capture_output=True, text=True, timeout=30, cwd=ROOT,
                               check=False)
    assert completed.returncode == 0, completed.stdout[:200]
    return json.loads(completed.stdout)


class HexagramTableContractTests(unittest.TestCase):
    def test_all_64_entries_code_name_metadata_consistent(self):
        entries = load_entries()
        self.assertEqual(len(entries), 64, "六十四卦条目数不足/超出")
        codes = [e[0] for e in entries]
        self.assertEqual(len(set(codes)), 64, "卦码重复")
        for code, name, _meaning, _fe, _shi, _ying, _palace, inner, outer, _kind in entries:
            exp_inner, exp_outer = TRI[code[:3]], TRI[code[3:]]
            nm_inner, nm_outer = name_trigrams(name)
            self.assertEqual((nm_inner, nm_outer), (exp_inner, exp_outer),
                             f"卦名与卦码不符: {code} {name}")
            self.assertEqual((inner, outer), (exp_inner, exp_outer),
                             f"inner/outer 与卦码互反(DEF-7 回归): {code} {name} "
                             f"表=({inner},{outer}) 应=({exp_inner},{exp_outer})")

    def test_palace_structure_rules(self):
        for code, name, _meaning, _fe, _shi, _ying, palace, inner, outer, kind in load_entries():
            if kind == "本宫":
                self.assertEqual((inner, outer), (palace, palace),
                                 f"本宫卦上下卦应皆为宫卦: {name}")
            elif kind == "归魂":
                self.assertEqual(inner, palace,
                                 f"归魂卦内卦应为宫卦: {name}")
        kinds = {}
        for *_, kind in load_entries():
            kinds[kind] = kinds.get(kind, 0) + 1
        self.assertEqual(kinds.get("本宫"), 8, "本宫卦应8条")
        self.assertEqual(kinds.get("归魂"), 8, "归魂卦应8条")
        self.assertEqual(kinds.get("游魂"), 8, "游魂卦应8条")

    def test_engine_najia_goldens_for_fixed_rows(self):
        """DEF-7 行为级验证（需已构建 liu_yao_web_cli）。"""
        if not BIN.exists():
            self.skipTest("liu_yao_web_cli 未构建")
        # 地水师本卦：内卦坎 → 初爻支寅（修复前按坤纳 未）
        plate = run({**DATE, "hexagram_code": "010000", "changing_lines": [2]})
        y1 = next(y for y in plate["yao"] if y["position"] == 1)
        self.assertEqual(y1["mainPillar"]["branch"], "寅", "师卦初爻纳支应为寅（坎内）")
        # 天火同人本卦：内卦离 → 初爻支卯（修复前按乾纳 子）
        plate = run({**DATE, "hexagram_code": "101111", "changing_lines": [3]})
        y1 = next(y for y in plate["yao"] if y["position"] == 1)
        self.assertEqual(y1["mainPillar"]["branch"], "卯", "同人卦初爻纳支应为卯（离内）")
        # 乾卦二爻动 → 变卦天火同人，二爻变支应为 丑（离内二位；修复前 寅→寅）
        plate = run({**DATE, "hexagram_code": "111111", "changing_lines": [2]})
        y2 = next(y for y in plate["yao"] if y["position"] == 2)
        self.assertEqual(y2["mainPillar"]["branch"], "寅")
        self.assertEqual((y2.get("changedPillar") or {}).get("branch"), "丑",
                         "乾二爻动变同人，变支应为丑（DEF-7 回归锁）")


if __name__ == "__main__":
    unittest.main()
