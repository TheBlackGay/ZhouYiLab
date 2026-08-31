import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "web"))

from ziwei_pattern_engine import (  # noqa: E402
    PatternConfigError,
    load_pattern_catalog,
    match_pattern,
    run_catalog_examples,
)


PATTERN_DIR = PROJECT_ROOT / "config" / "ziwei" / "patterns"


def star(name, transformation=None, source_layer="natal", palace="命宫"):
    return {
        "name": name,
        "transformation": transformation,
        "source_layer": source_layer,
        "physical_palace": palace,
        "relation": "self",
    }


def context(focus="命宫", layer="natal", **scopes):
    defaults = {
        "self": {"stars": []},
        "triads": {"stars": []},
        "opposite": {"stars": []},
        "four_directions": {"stars": []},
        "adjacent_left": {"stars": []},
        "adjacent_right": {"stars": []},
    }
    defaults.update(scopes)
    return {
        "layer": {"id": layer, "name": layer},
        "focus": {"name": focus, "effect_subject": [f"{focus}主题"]},
        "scopes": defaults,
    }


def base_pattern():
    return {
        "schema_version": "1.0.0",
        "id": "pattern.test",
        "revision": 1,
        "enabled": True,
        "name": "测试格局",
        "category": "test",
        "school": "测试",
        "strictness": "strict",
        "applicable_layers": ["natal"],
        "applicable_focus_palaces": ["*"],
        "required": {
            "all": [{
                "id": "required_star",
                "name": "必要星曜",
                "predicate": "star.contains",
                "scope": "self",
                "values": ["紫微"],
            }]
        },
        "enhancers": [],
        "weakeners": [],
        "breakers": [],
        "status_policy": {
            "required_matched": "formed",
            "enhancer_matched": "strengthened",
            "weakener_matched": "weakened",
            "breaker_matched": "broken",
            "tendency_matched": "tendency",
        },
        "result": {
            "nature": "neutral",
            "summary": "测试",
            "interpretation_template": "测试",
        },
        "examples": [{
            "name": "最小正例",
            "context": context(self={"stars": [star("紫微")]}),
            "expected": {"matched": True},
        }],
    }


class ZiWeiPatternEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_pattern_catalog(PATTERN_DIR)

    def test_all_embedded_examples_pass(self):
        failures = [case for case in run_catalog_examples(self.catalog) if not case["passed"]]
        self.assertEqual([], failures)

    def test_same_pattern_is_attributed_to_each_focus_palace(self):
        pattern = deepcopy(base_pattern())
        life = match_pattern(pattern, context("命宫", self={"stars": [star("紫微")]}))
        parents = match_pattern(pattern, context("父母宫", self={"stars": [star("紫微")]}))
        self.assertEqual("命宫", life["effect_palace"])
        self.assertEqual("父母宫", parents["effect_palace"])
        self.assertNotEqual(life["effect_subject"], parents["effect_subject"])

    def test_transformations_from_different_layers_cannot_form_pattern(self):
        pattern = next(
            item for item in self.catalog["patterns"]
            if item["id"] == "pattern.sanqi.four_directions"
        )
        result = match_pattern(pattern, context(
            layer="annual",
            four_directions={"stars": [
                star("廉贞", "化禄", "natal"),
                star("破军", "化权", "decade"),
                star("武曲", "化科", "annual"),
            ]},
        ))
        self.assertIsNone(result)

    def test_modifier_precedence_is_breaker_then_weakener_then_enhancer(self):
        pattern = base_pattern()
        for group, value in (
            ("enhancers", "左辅"), ("weakeners", "火星"), ("breakers", "化忌")
        ):
            pattern[group] = [{
                "id": group,
                "name": group,
                "predicate": "star.contains",
                "scope": "four_directions",
                "values": [value],
            }]
        result = match_pattern(pattern, context(
            self={"stars": [star("紫微")]},
            four_directions={"stars": [star("左辅"), star("火星"), star("化忌")]},
        ))
        self.assertEqual("broken", result["status"])
        self.assertTrue(result["enhancers"])
        self.assertTrue(result["weakeners"])
        self.assertTrue(result["breakers"])

    def test_tendency_requires_explicit_condition(self):
        pattern = base_pattern()
        no_match = match_pattern(pattern, context(self={"stars": [star("天府")]}))
        self.assertIsNone(no_match)
        pattern["tendency_conditions"] = {
            "all": [{
                "id": "tendency_star",
                "name": "倾向星曜",
                "predicate": "star.contains",
                "scope": "self",
                "values": ["天府"],
            }]
        }
        tendency = match_pattern(pattern, context(self={"stars": [star("天府")]}))
        self.assertEqual("tendency", tendency["status"])

    def test_match_contains_condition_trace_and_star_evidence(self):
        result = match_pattern(
            base_pattern(), context(self={"stars": [star("紫微", palace="父母宫")]})
        )
        self.assertTrue(result["required_trace"]["matched"])
        leaf = result["matched_conditions"][0]
        self.assertEqual("required_star", leaf["condition_id"])
        self.assertEqual("紫微", leaf["evidence"][0]["star"])
        self.assertEqual("父母宫", leaf["evidence"][0]["physical_palace"])

    def test_invalid_catalogs_fail_validation(self):
        invalid_cases = []
        unknown_predicate = base_pattern()
        unknown_predicate["required"]["all"][0]["predicate"] = "python.eval"
        invalid_cases.append((unknown_predicate, "不支持谓词"))
        invalid_layer = base_pattern()
        invalid_layer["applicable_layers"] = ["future"]
        invalid_cases.append((invalid_layer, "不支持的盘层"))
        invalid_scope = base_pattern()
        invalid_scope["required"]["all"][0]["scope"] = "nearby"
        invalid_cases.append((invalid_scope, "scope 无效"))
        invalid_status = base_pattern()
        invalid_status["status_policy"]["required_matched"] = "maybe"
        invalid_cases.append((invalid_status, "状态无效"))

        for pattern, message in invalid_cases:
            with self.subTest(message=message):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / "_manifest.json").write_text(json.dumps({
                        "schema_version": "1.0.0",
                        "ruleset": "test",
                        "pattern_count": 1,
                    }), encoding="utf-8")
                    (root / "rule.json").write_text(
                        json.dumps(pattern, ensure_ascii=False), encoding="utf-8"
                    )
                    with self.assertRaisesRegex(PatternConfigError, message):
                        load_pattern_catalog(root)

    def test_duplicate_pattern_ids_fail_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "_manifest.json").write_text(json.dumps({
                "schema_version": "1.0.0",
                "ruleset": "test",
                "pattern_count": 2,
            }), encoding="utf-8")
            payload = json.dumps(base_pattern(), ensure_ascii=False)
            (root / "one.json").write_text(payload, encoding="utf-8")
            (root / "two.json").write_text(payload, encoding="utf-8")
            with self.assertRaisesRegex(PatternConfigError, "格局 ID 重复"):
                load_pattern_catalog(root)


if __name__ == "__main__":
    unittest.main()
