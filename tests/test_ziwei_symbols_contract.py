"""P0-4 符号字典单源化契约。

链路：C++ 内核 `symbols` operation（权威）
  → web /api/v1/ziwei/symbols（透传+缓存）
  → config/ziwei/symbolism_dictionary.json（必须 ⊆ 内核符号集）
  → 格局引擎 known_star_names（加载期校验）。

本测试直接跑已构建的 zi_wei_web_cli；未构建时跳过（与既有 CLI 测试同风格）。
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIWEI_CLI = PROJECT_ROOT / "build" / "examples" / "zi_wei_web_cli"
DICTIONARY_PATH = PROJECT_ROOT / "config" / "ziwei" / "symbolism_dictionary.json"
PATTERNS_DIR = PROJECT_ROOT / "config" / "ziwei" / "patterns"
SERVER_SOURCE = (PROJECT_ROOT / "web" / "server.py").read_text(encoding="utf-8")


def run_symbols():
    completed = subprocess.run(
        [str(ZIWEI_CLI)], input=json.dumps({"operation": "symbols"}),
        capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT, check=False)
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert "error" not in payload, payload
    return payload


class ZiWeiSymbolsEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ZIWEI_CLI.exists():
            raise unittest.SkipTest("zi_wei_web_cli 尚未构建")
        cls.symbols = run_symbols()

    def test_symbols_shape(self):
        self.assertEqual(self.symbols["symbols_version"], "ziwei-symbols/1.1")
        stars = self.symbols["stars"]
        self.assertEqual(len(stars["zhu_xing"]), 14)
        self.assertEqual(len(stars["fu_xing"]), 14)
        self.assertEqual(len(self.symbols["brightness"]), 7)
        self.assertEqual(len(self.symbols["si_hua"]), 4)
        self.assertEqual(len(self.symbols["palaces"]), 12)
        self.assertEqual(len(self.symbols["heavenly_stems"]), 10)
        self.assertEqual(len(self.symbols["earthly_branches"]), 12)
        self.assertEqual(len(self.symbols["five_elements"]), 5)
        for name in self.symbols["all_star_names"]:
            self.assertTrue(name.strip(), "符号名不得为空白")

    def test_star_temperament_is_kernel_sourced(self):
        """1.1 星性档案：主辅煞全覆盖，五行/阴阳非空，供分布画像消费。"""
        temperament = self.symbols["star_temperament"]
        by_name = {entry["name"]: entry for entry in temperament}
        self.assertGreaterEqual(len(by_name), 28)
        for star in ("紫微", "天机", "太阳", "左辅", "擎羊", "火星"):
            entry = by_name.get(star)
            self.assertIsNotNone(entry, f"星性档案缺 {star}")
            self.assertIn(entry["element"], {"金", "木", "水", "火", "土"})
            self.assertIn(entry["polarity"], {"阴", "阳"})
        groups = {entry["group"] for entry in temperament}
        self.assertTrue({"zhu_xing", "fu_xing", "sha_xing"} <= groups)

    def test_star_enums_are_covered(self):
        """枚举侧权威名必须在符号集中（历史上 ZaYao 文档库缺 截路/空亡）。"""
        all_names = set(self.symbols["all_star_names"])
        for name in ("截路", "空亡", "截空"):
            self.assertIn(name, all_names)

    def test_symbolism_dictionary_is_subset_of_kernel_symbols(self):
        """象义词典的星名必须全部是内核可上盘星名（拼错在审计期暴露）。"""
        dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
        kernel = set(self.symbols["all_star_names"])
        unknown = sorted(
            entry["name"] for entry in dictionary["stars"]
            if entry["name"] not in kernel
        )
        self.assertEqual(unknown, [], "symbolism_dictionary 含内核未知星名")

    def test_pattern_catalog_validates_against_kernel_symbols(self):
        """格局引擎用内核符号全集做 known_star_names 也能加载 → 规则库无越界星名。"""
        from ziwei_pattern_engine import load_pattern_catalog
        catalog = load_pattern_catalog(
            PATTERNS_DIR, set(self.symbols["all_star_names"]))
        self.assertGreaterEqual(len(catalog["patterns"]), 39)


class ZiWeiSymbolsHttpContractTests(unittest.TestCase):
    def test_server_exposes_symbols_endpoint(self):
        self.assertIn('"/api/v1/ziwei/symbols"', SERVER_SOURCE)
        self.assertIn("def _ziwei_symbols", SERVER_SOURCE)

    def test_manifest_declares_symbols_route(self):
        manifest = json.loads(
            (PROJECT_ROOT / "config" / "platform" / "tools" / "ziwei.json")
            .read_text(encoding="utf-8"))
        paths = {route["path"] for route in manifest["routes"]}
        self.assertIn("/api/v1/ziwei/symbols", paths)


if __name__ == "__main__":
    unittest.main()
