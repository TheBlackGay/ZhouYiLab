"""六爻案例库契约（liuyao-case/1.0，A3 结构层）。

覆盖：
* 库结构：schema/manifest/案例文件三方一致；id 唯一合法；
  classic 例必带 book/case_ref 且 verification=pending_manual_collation（诚实闸：
  未经人工校勘的古籍例不得标 self_consistent，且 status 只能 pending）；
  structural 例必须 self_consistent 且 status ∈ {boundary, calibrated}；
* expected 路径合法（点分段，数字段按 position 寻址 yao 数组）；
* 真盘执行：逐例经 liu_yao_web_cli 重放，expected 全路径比对
  （列表值以逗号连接串比较）；二进制未构建时跳过。
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "config" / "liuyao" / "cases"
CLI = ROOT / "build" / "examples" / "liu_yao_web_cli"

ID_RE = re.compile(r"^[a-z0-9_]+$")
PATH_RE = re.compile(r"^[a-z_][A-Za-z0-9_]*(\.[a-zA-Z_0-9][A-Za-z0-9_]*)*$")
REQUIRED = ("schema", "id", "status", "input", "expected", "source_case")
STATUSES = {"pending", "calibrated", "boundary"}
ORIGINS = {"classic_example", "structural_regression"}
VERIFICATIONS = {"pending_manual_collation", "self_consistent"}


def resolve(plate, dotted):
    node = plate
    for part in dotted.split("."):
        if isinstance(node, list):
            assert part.isdigit(), f"数组层必须用 position 数字段寻址: {dotted}"
            node = next(e for e in node if e.get("position") == int(part))
        else:
            assert isinstance(node, dict) and part in node, f"事实盘缺字段 {dotted}"
            node = node[part]
    return node


def as_comparable(value):
    if isinstance(value, list):
        return ",".join(str(x) for x in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class LiuYaoCasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads((CASES_DIR / "_manifest.json").read_text(encoding="utf-8"))
        files = sorted(p for p in CASES_DIR.glob("*.json")
                       if p.name not in ("case.schema.json", "_manifest.json"))
        cls.manifest = manifest
        cls.cases = [json.loads(p.read_text(encoding="utf-8")) for p in files]

    def test_library_structure(self):
        self.assertEqual(self.manifest["schema"], "liuyao-case-manifest/1.0")
        self.assertEqual(self.manifest["school"], "liuyao-zengshan")
        self.assertEqual(self.manifest["calibration_stage"], "stage1_plate_facts")
        ids = [case["id"] for case in self.cases]
        self.assertEqual(sorted(ids), sorted(set(ids)), "案例 id 必须唯一")
        self.assertEqual(sorted(self.manifest["cases"]), sorted(ids),
                         "manifest 与案例文件必须一一对应")
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(case["schema"], "liuyao-case/1.0")
                self.assertTrue(ID_RE.match(case["id"]))
                self.assertEqual(set(case), set(REQUIRED))
                self.assertIn(case["status"], STATUSES)
                inp = case["input"]
                self.assertRegex(inp["hexagram_code"], r"^[01]{6}$")
                self.assertTrue(all(1 <= n <= 6 for n in inp.get("changing_lines", [])))
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
                    self.assertTrue(PATH_RE.match(path), f"非法点分路径 {path}")

    def test_cases_replay_against_engine(self):
        if not CLI.exists():
            self.skipTest("liu_yao_web_cli 未构建")
        for case in self.cases:
            with self.subTest(case=case["id"]):
                payload = {**case["input"]}
                payload.setdefault("calendar", "solar")
                completed = subprocess.run([str(CLI)], input=json.dumps(payload),
                                           capture_output=True, text=True,
                                           timeout=30, cwd=ROOT, check=False)
                self.assertEqual(completed.returncode, 0, case["id"])
                plate = json.loads(completed.stdout)
                for path, expect in case["expected"].items():
                    got = resolve(plate, path)
                    self.assertEqual(as_comparable(got), as_comparable(expect),
                                     f"{case['id']}·{path}")


if __name__ == "__main__":
    unittest.main()
