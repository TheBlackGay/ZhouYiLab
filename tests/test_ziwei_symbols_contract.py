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

    def test_changsheng12_batch1_cross_locks(self):
        """B9 批次一（D4=A，2026-09-21）：长生十二神入库三重交叉锁。

        ① 典内 12 条次序 == 内核 ChangSheng12 枚举中文映射序；
        ② 条目 id == shen_sha_dictionary.chang_sheng_12（职能层）id；
        ③ 释义禁吉凶断语色彩词；coverage/version 联动 1.1.0。
        """
        import re
        src = (PROJECT_ROOT / "src" / "zi_wei" / "zi_wei_constants.cppm").read_text(
            encoding="utf-8")
        block = re.search(r"struct ZhMap<ChangSheng12>.*?std::array\{(.*?)\};",
                          src, re.S)
        self.assertIsNotNone(block, "内核 ChangSheng12 中文映射未找到（源结构变更请同步）")
        kernel_order = re.findall(r'"([^"]+)"sv', block.group(1))
        self.assertEqual(len(kernel_order), 12)

        dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
        entries = [e for e in dictionary["stars"] if e.get("system") == "长生十二神"]
        self.assertEqual(len(entries), 12)
        by_order = sorted(entries, key=lambda e: e["attributes"]["stage_order"])
        self.assertEqual([e["name"] for e in by_order], kernel_order,
                         "stage_order 必须与内核枚举序逐位一致")
        self.assertTrue(set(kernel_order) <= set(self.symbols["all_star_names"]))

        shen_sha = json.loads(
            (PROJECT_ROOT / "config" / "ziwei" / "shen_sha_dictionary.json")
            .read_text(encoding="utf-8"))
        func = shen_sha["systems"]["chang_sheng_12"]["entries"]
        for entry in entries:
            self.assertEqual(entry["id"], func[entry["name"]]["id"],
                             f"{entry['name']} 与职能字典 id 失锁")

        banned = ("主吉", "主凶", "大吉", "大凶", "富贵", "贫贱", "寿夭", "凶丧")
        for entry in entries:
            blob = json.dumps(entry, ensure_ascii=False)
            for word in banned:
                self.assertNotIn(word, blob, f"{entry['name']} 释义含禁断语词 {word}")

        self.assertGreaterEqual(
            tuple(int(x) for x in dictionary["dictionary_version"].split(".")), (1, 1),
            "批次一入库后字典版本须 ≥1.1.0")
        self.assertEqual(
            dictionary["coverage"]["miscellaneous_stars"]["configured"],
            len(dictionary["stars"]) - 28, "coverage 计数须等于非本/辅核心条目数")

    def test_shensha_batch2_cross_locks(self):
        """B9 批次二（D4=A，2026-09-21）：博士/岁前/将前三系年煞全量交叉锁。

        ① 三系 36 memberships（12×3）逐星逐位 == 内核枚举序（attributes.orders）；
        ② 28 条新入典条目 id == 职能层 id（重名重 id 者按文档化后缀消歧：
           岁前官符 guan_fu_sui_qian、将前息神 xi_shen_jiang_qian）；
        ③ 新条目 derived 之 meaning/boundary == 职能层 key_effect/boundary 原文；
        ④ 典内 id、星名全局唯一；禁吉凶断语词；版本钉 1.2.0。
        """
        import re
        src = (PROJECT_ROOT / "src" / "zi_wei" / "zi_wei_constants.cppm").read_text(
            encoding="utf-8")
        enums = {}
        for enum, label in (("BoShi12", "博士十二神"), ("SuiQian12", "岁前十二神"),
                            ("JiangQian12", "将前十二神")):
            block = re.search(rf"struct ZhMap<{enum}>.*?std::array\{{(.*?)\}};",
                              src, re.S)
            self.assertIsNotNone(block, f"内核 {enum} 中文映射未找到")
            enums[label] = re.findall(r'"([^"]+)"sv', block.group(1))
            self.assertEqual(len(enums[label]), 12)

        dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
        stars = dictionary["stars"]
        shen_sha = json.loads(
            (PROJECT_ROOT / "config" / "ziwei" / "shen_sha_dictionary.json")
            .read_text(encoding="utf-8"))
        func = {}
        for sysid, label in (("bo_shi_12", "博士十二神"), ("sui_qian_12", "岁前十二神"),
                             ("jiang_qian_12", "将前十二神")):
            func[label] = shen_sha["systems"][sysid]["entries"]

        # ① 36 memberships 全量序锁
        for label, names in enums.items():
            for idx, name in enumerate(names, start=1):
                hits = [e for e in stars
                        if e["name"] == name
                        and e.get("attributes", {}).get("orders", {}).get(label) == idx]
                self.assertEqual(len(hits), 1,
                                 f"{label}·{name} 序位 {idx} 交叉锁失配（命中 {len(hits)} 条）")

        # ②③ 28 条新入典（system 即三系标签之一）：id + 职能层文本一致
        new_entries = [e for e in stars if e.get("system") in enums]
        self.assertEqual(len(new_entries), 28)
        suffix = {("官符", "岁前十二神"): "_sui_qian",
                  ("息神", "将前十二神"): "_jiang_qian"}
        for e in new_entries:
            expect = func[e["system"]][e["name"]]["id"] + suffix.get(
                (e["name"], e["system"]), "")
            self.assertEqual(e["id"], expect, f"{e['name']} id 失锁")
            d0 = e["derived_definitions"][0]
            self.assertEqual(d0["meaning"],
                             func[e["system"]][e["name"]]["key_effect"],
                             f"{e['name']} derived meaning 与职能层失锁")
            self.assertTrue(d0["boundary"].endswith(
                func[e["system"]][e["name"]]["boundary"]),
                f"{e['name']} boundary 未包含职能层原文")

        # ④ 唯一性 + 禁断语 + 版本
        ids = [e["id"] for e in stars]
        self.assertEqual(len(ids), len(set(ids)), "典内 id 重复")
        names = [e["name"] for e in stars]
        self.assertEqual(len(names), len(set(names)), "典内星名重复")
        banned = ("主吉", "主凶", "大吉", "大凶", "富贵", "贫贱", "寿夭", "凶丧")
        for e in new_entries:
            blob = json.dumps(e, ensure_ascii=False)
            for word in banned:
                self.assertNotIn(word, blob, f"{e['name']} 释义含禁断语词 {word}")
        self.assertGreaterEqual(
            tuple(int(x) for x in dictionary["dictionary_version"].split(".")), (1, 2),
            "批次二入库后字典版本须 ≥1.2.0")
        self.assertEqual(
            dictionary["coverage"]["miscellaneous_stars"]["configured"],
            len(stars) - 28)

    def test_full_kernel_coverage_batch3_capstone(self):
        """B9 批次三封顶（2026-09-21）：字典星名 == 内核符号全集，缺收清零。

        天解/截空属性反向锁内核杂曜文档（zi_wei_star_doc_za_yao）；
        全典禁吉凶断语词仅对新三例执行（既有 67 条为先行审定资产不追溯改文）；
        版本钉 1.3.0。"""
        import re
        dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
        names = {e["name"] for e in dictionary["stars"]}
        missing = sorted(set(self.symbols["all_star_names"]) - names)
        self.assertEqual(missing, [], "字典必须全覆盖内核符号集（B9 DoD）")
        self.assertEqual(dictionary["dictionary_version"], "1.3.0")

        doc = (PROJECT_ROOT / "src" / "zi_wei" / "zi_wei_star_doc_za_yao.cpp"
               ).read_text(encoding="utf-8")
        wux = {"Huo": "火", "Mu": "木", "Shui": "水", "Jin": "金", "Tu": "土"}
        for star in ("天解", "截空"):
            m = re.search(rf'\{{"{star}", \{{(.*?)\}}\}},?\s*(?=\{{"|std::|$)',
                          doc, re.S)
            self.assertIsNotNone(m, f"内核杂曜文档缺 {star}")
            entry = next(e for e in dictionary["stars"] if e["name"] == star)
            self.assertEqual(entry["attributes"]["element"],
                             wux[re.search(r'wu_xing = XingYaoWuXing::(\w+)',
                                           m.group(1)).group(1)],
                             f"{star} 五行与内核失锁")
            self.assertEqual(entry["attributes"]["yin_yang"],
                             {"Yang": "阳", "Yin": "阴"}[re.search(
                                 r'yin_yang = XingYaoYinYang::(\w+)',
                                 m.group(1)).group(1)],
                             f"{star} 阴阳与内核失锁")
            self.assertEqual(entry["attributes"]["hua_qi"],
                             re.search(r'hua_qi = "([^"]*)"', m.group(1)).group(1),
                             f"{star} 化气与内核失锁")
        banned = ("主吉", "主凶", "大吉", "大凶", "富贵", "贫贱", "寿夭", "凶丧")
        for star in ("天解", "截空"):
            entry = next(e for e in dictionary["stars"] if e["name"] == star)
            blob = json.dumps(entry, ensure_ascii=False)
            for word in banned:
                self.assertNotIn(word, blob, f"{star} 释义含禁断语词")

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
