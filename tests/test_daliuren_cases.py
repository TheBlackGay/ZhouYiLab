"""大六壬案例库契约（daliuren-case/1.0，A3 结构层）。

覆盖：
* 库结构三方一致（schema/manifest/案例文件）、id 唯一合法；
  classic 例必带 book/case_ref 且 verification=pending_manual_collation + status=pending
  （诚实闸）；structural 例必须 self_consistent 且 status ∈ {boundary, calibrated}；
* expected 路径合法（点分段，允许 '[]' 数组字段提取段与 position 数字段）；
* 输入合法（calendar/date/yuejiang_method 枚举）；
* 真盘执行：逐例经 da_liu_ren_web_cli 重放，expected 全路径比对
  （'[]' 段按序提取字段逗号连接比较；bool 以 true/false 串比较）。
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "config" / "daliuren" / "cases"
CLI = ROOT / "build" / "examples" / "da_liu_ren_web_cli"

ID_RE = re.compile(r"^[a-z0-9_]+$")
PATH_RE = re.compile(r"^[a-z_][A-Za-z0-9_]*(\[\])?(\.[A-Za-z_0-9][A-Za-z0-9_]*(\[\])?)*$")
REQUIRED = ("schema", "id", "status", "input", "expected", "source_case")
STATUSES = {"pending", "calibrated", "boundary"}
ORIGINS = {"classic_example", "structural_regression"}
VERIFICATIONS = {"pending_manual_collation", "self_consistent"}
YUEJIANG = {"zhongqi", "guifa_suicha"}


def resolve(plate, dotted):
    parts = dotted.split(".")
    i = 0
    while i < len(parts):
        seg = parts[i]
        if seg.endswith("[]"):
            arr = plate[seg[:-2]] if isinstance(plate, dict) else plate
            assert i + 1 < len(parts), f"'[]' 段后必须接字段段: {dotted}"
            return ",".join(str(it[parts[i + 1]]) for it in arr)
        if isinstance(plate, list):
            assert seg.isdigit(), f"数组层须 position 数字段或 '[]' 提取: {dotted}"
            plate = next(e for e in plate if e.get("position") == int(seg))
        else:
            assert isinstance(plate, dict) and seg in plate, f"事实盘缺字段 {dotted}"
            plate = plate[seg]
        i += 1
    return plate


def as_comparable(value):
    if isinstance(value, list):
        return ",".join(str(x) for x in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class DaLiuRenCasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((CASES_DIR / "_manifest.json").read_text(encoding="utf-8"))
        files = sorted(p for p in CASES_DIR.glob("*.json")
                       if p.name not in ("case.schema.json", "_manifest.json"))
        cls.cases = [json.loads(p.read_text(encoding="utf-8")) for p in files]

    def test_library_structure(self):
        self.assertEqual(self.manifest["schema"], "daliuren-case-manifest/1.0")
        self.assertEqual(self.manifest["calibration_stage"], "stage1_plate_facts")
        ids = [c["id"] for c in self.cases]
        self.assertEqual(sorted(ids), sorted(set(ids)), "案例 id 必须唯一")
        self.assertEqual(sorted(self.manifest["cases"]), sorted(ids),
                         "manifest 与案例文件必须一一对应")
        self.assertGreaterEqual(len(ids), 6)
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(case["schema"], "daliuren-case/1.0")
                self.assertTrue(ID_RE.match(case["id"]))
                self.assertEqual(set(case), set(REQUIRED))
                self.assertIn(case["status"], STATUSES)
                inp = case["input"]
                self.assertIn(inp.get("calendar", "solar"), {"solar", "lunar"})
                for k in ("year", "month", "day"):
                    self.assertIn(k, inp["date"])
                self.assertIn(inp.get("yuejiang_method", "zhongqi"), YUEJIANG)
                source = case["source_case"]
                self.assertIn(source["origin"], ORIGINS)
                self.assertIn(source.get("verification"), VERIFICATIONS)
                if source["origin"] == "classic_example":
                    self.assertIn("book", source)
                    self.assertIn("case_ref", source)
                    self.assertEqual(source["verification"], "pending_manual_collation",
                                     "古籍例未经人工校勘不得标 self_consistent")
                    self.assertEqual(case["status"], "pending",
                                     "未校勘古籍例不得充当已校验收口")
                else:
                    self.assertEqual(source["verification"], "self_consistent")
                    self.assertIn(case["status"], {"boundary", "calibrated"})
                for path in case["expected"]:
                    self.assertTrue(PATH_RE.match(path), f"非法路径 {path}")

    def test_cases_replay_against_engine(self):
        if not CLI.exists():
            self.skipTest("da_liu_ren_web_cli 未构建")
        for case in self.cases:
            with self.subTest(case=case["id"]):
                completed = subprocess.run([str(CLI)], input=json.dumps(case["input"]),
                                           capture_output=True, text=True,
                                           timeout=30, cwd=ROOT, check=False)
                self.assertEqual(completed.returncode, 0, case["id"])
                plate = json.loads(completed.stdout)
                self.assertNotIn("error", plate, case["id"])
                for path, expect in case["expected"].items():
                    got = resolve(plate, path)
                    self.assertEqual(as_comparable(got), as_comparable(expect),
                                     f"{case['id']}·{path}")


if __name__ == "__main__":
    unittest.main()
