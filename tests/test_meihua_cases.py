"""梅花易数案例库契约（meihua-case/1.0，M3）。

覆盖：
* 库结构完整性：schema/manifest/案例文件三方一致，id 唯一且合法，
  classic 例必带 book/case_ref 且 verification=pending_manual_collation
  （诚实闸：未经人工校勘的古籍例不允许标 self_consistent）；
* expected 全为点分路径，禁止 palace 进入锁定（见 cases/README 边界声明）；
* 真盘执行：每例经 mei_hua_web_cli 跑盘面，expected 逐路径比对
  （reported 数组以逗号串比对，兼容标量 schema）；二进制未构建时跳过。
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "config" / "meihua/cases"
CLI = ROOT / "build" / "examples" / "mei_hua_web_cli"

ID_RE = re.compile(r"^[a-z0-9_]+$")
PATH_RE = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$")
REQUIRED = ("schema", "id", "status", "input", "expected", "source_case")
STATUSES = {"pending", "calibrated", "boundary"}
ORIGINS = {"classic_example", "structural_regression"}
VERIFICATIONS = {"pending_manual_collation", "self_consistent"}


def load_cases():
    manifest = json.loads((CASES_DIR / "_manifest.json").read_text(encoding="utf-8"))
    files = sorted(p for p in CASES_DIR.glob("*.json")
                   if p.name not in ("case.schema.json", "_manifest.json"))
    return manifest, files


def resolve(plate, dotted):
    node = plate
    for part in dotted.split("."):
        assert isinstance(node, dict) and part in node, f"事实盘缺字段 {dotted}"
        node = node[part]
    return node


class MeiHuaCasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.files = load_cases()
        cls.cases = [json.loads(p.read_text(encoding="utf-8")) for p in cls.files]

    def test_library_structure(self):
        self.assertEqual(self.manifest["schema"], "meihua-case-manifest/1.0")
        self.assertEqual(self.manifest["calibration_stage"], "stage1_plate_facts")
        ids = [case["id"] for case in self.cases]
        self.assertEqual(sorted(ids), sorted(set(ids)), "案例 id 必须唯一")
        self.assertEqual(sorted(self.manifest["cases"]), sorted(ids),
                         "manifest 与案例文件必须一一对应")
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(case["schema"], "meihua-case/1.0")
                self.assertTrue(ID_RE.match(case["id"]))
                self.assertEqual(set(case), set(REQUIRED))
                self.assertIn(case["status"], STATUSES)
                source = case["source_case"]
                self.assertIn(source["origin"], ORIGINS)
                self.assertIn(source["verification"], VERIFICATIONS)
                if source["origin"] == "classic_example":
                    self.assertIn("book", source)
                    self.assertIn("case_ref", source)
                    self.assertEqual(source["verification"], "pending_manual_collation",
                                     "古籍例未经人工校勘不得标 self_consistent")
                else:
                    self.assertEqual(source["verification"], "self_consistent")

    def test_expected_paths_are_dot_paths_without_palace(self):
        for case in self.cases:
            for path in case["expected"]:
                with self.subTest(case=case["id"], path=path):
                    self.assertTrue(PATH_RE.match(path), f"expected 键须为事实盘点路径: {path}")
                    self.assertNotIn("palace", path, "宫位字段不进案例锁（见 README 边界）")

    def test_all_cases_pass_against_engine(self):
        if not CLI.exists():
            self.skipTest("mei_hua_web_cli 未构建")
        for case in self.cases:
            with self.subTest(case=case["id"]):
                completed = subprocess.run(
                    [str(CLI)], input=json.dumps(case["input"], ensure_ascii=False),
                    capture_output=True, text=True, timeout=30, cwd=ROOT, check=False)
                self.assertEqual(completed.returncode, 0, completed.stdout[:200])
                plate = json.loads(completed.stdout)
                for path, want in case["expected"].items():
                    got = resolve(plate, path)
                    if isinstance(got, list):
                        self.assertEqual(",".join(str(x) for x in got), want, path)
                    else:
                        self.assertEqual(got, want, path)


if __name__ == "__main__":
    unittest.main()
