"""大六壬 2.0.0 I2：术语帮助词典契约（DLR-204）。

术语库是页面帮助弹层与专业视图内联提示的唯一来源：
* 十条必选术语齐全，每条必须给出"当前实现口径"；
* 声明了 related_profile_rule 的术语必须对齐引擎 rule_profile 实际键；
* 词典经注册表 static_config 路由（清单声明）只读暴露，不新增手写分支。
"""
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_PATH = PROJECT_ROOT / "config" / "daliuren" / "glossary.json"
SCHEMA_PATH = PROJECT_ROOT / "config" / "daliuren" / "glossary.schema.json"
MANIFEST_PATH = PROJECT_ROOT / "config" / "platform" / "tools" / "da_liu_ren.json"

# DLR-204 明确列出的十个术语（id 与页面 data-glossary 锚点一致）。
REQUIRED_TERMS = {
    "si_ke", "san_chuan", "chu_chuan", "zhong_chuan", "mo_chuan",
    "yue_jiang", "gui_ren", "ke_shi", "liu_qin", "xun_kong",
}
# 引擎 meta.rule_profile 的规则键（tests/test_da_liu_ren_engine_contract.py 同源）。
PROFILE_RULE_KEYS = {
    "four_pillars", "time_granularity", "yue_jiang", "gui_ren", "shen_jiang",
    "gan_ji_gong", "san_chuan", "dun_gan", "liu_qin", "gua_ti",
}


class DaLiuRenGlossaryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glossary = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
        cls.terms = {term["id"]: term for term in cls.glossary["terms"]}

    def test_schema_shape_and_version(self):
        self.assertEqual(self.glossary["schema"], "daliuren-glossary/1.0")
        self.assertTrue(self.glossary["glossary_version"].strip())
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], "daliuren-glossary/1.0")

    def test_required_terms_present_and_caliber_annotated(self):
        missing = REQUIRED_TERMS - set(self.terms)
        self.assertEqual(missing, set(), "DLR-204 要求的术语不得缺失")
        for term_id, term in self.terms.items():
            self.assertTrue(term.get("term", "").strip(), f"{term_id} 缺术语名")
            self.assertGreaterEqual(len(term.get("definition", "")), 8,
                                    f"{term_id} 定义过短")
            self.assertTrue(term.get("caliber", "").strip(),
                            f"{term_id} 必须标注当前页面口径")

    def test_profile_rule_cross_reference_is_valid(self):
        for term_id, term in self.terms.items():
            rule = term.get("related_profile_rule")
            if rule is not None:
                self.assertIn(rule, PROFILE_RULE_KEYS,
                              f"{term_id} 引用了引擎不存在的口径键 {rule}")

    def test_no_deterministic_auspice_claims(self):
        """2.0.0 明确不做自动断语；术语与口径不得混入确定性吉凶词。"""
        banned = ("主大吉", "必凶", "定应", "必然发财", "必死")
        for term in self.glossary["terms"]:
            text = term["definition"] + term["caliber"]
            for word in banned:
                self.assertNotIn(word, text, f"{term['id']} 出现断语词 {word}")

    def test_exposed_via_registry_not_hand_written_branch(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        route = next((r for r in manifest["routes"]
                      if r["path"] == "/api/v1/da-liu-ren/glossary"), None)
        self.assertIsNotNone(route, "术语路由必须由清单声明")
        self.assertEqual(route["method"], "GET")
        self.assertEqual(route["handler"], "static_config")
        self.assertEqual(route["options"]["config_path"], "config/daliuren/glossary.json")


if __name__ == "__main__":
    unittest.main()
