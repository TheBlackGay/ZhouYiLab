import sys
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "web"))

from ziwei_research_engine import (  # noqa: E402
    ResearchConfigError,
    _validate_resources,
    load_research_resources,
    run_experiment,
)


class ZiWeiResearchEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources = load_research_resources()

    def test_all_frozen_pilot_cases_match_expectations(self):
        result = run_experiment(self.resources)
        self.assertTrue(result["passed"])
        self.assertEqual(8, result["case_count"])
        self.assertEqual(
            {f"LQ-{letter}" for letter in "ABCDEFGH"},
            {item["case_id"] for item in result["cases"]},
        )

    def test_lu_quan_case_preserves_independent_modifier_signals(self):
        result = run_experiment(self.resources, "LQ-D")["cases"][0]["result"]
        interaction = result["interactions"][0]
        matched = {
            item["id"] for item in interaction["modifiers"] if item["matched"]
        }
        self.assertEqual({
            "core_brightness_supported",
            "same_layer_hualu_support",
            "same_layer_huaquan_support",
        }, matched)
        self.assertFalse(result["aggregation"]["performed"])
        self.assertTrue(result["dimension_signals"]["resource_mobilization"])
        self.assertTrue(result["dimension_signals"]["authority_influence"])

        evidence_statuses = {
            fact.get("fact_status")
            for modifier in interaction["modifiers"] if modifier["matched"]
            for fact in modifier["evidence"]
        }
        self.assertIn("controlled_stimulus", evidence_statuses)

    def test_non_same_palace_and_single_star_cases_do_not_match_interaction(self):
        for case_id in ("LQ-F", "LQ-G", "LQ-H"):
            with self.subTest(case_id=case_id):
                result = run_experiment(self.resources, case_id)["cases"][0]["result"]
                self.assertEqual([], result["interactions"])
                self.assertTrue(result["profiles"])

    def test_huaji_case_keeps_brightness_and_risk_signals_together(self):
        result = run_experiment(self.resources, "LQ-E")["cases"][0]["result"]
        interaction = result["interactions"][0]
        matched = {
            item["id"] for item in interaction["modifiers"] if item["matched"]
        }
        self.assertEqual({"core_brightness_supported", "lianzhen_huaji"}, matched)
        risk_signal_ids = result["dimension_signals"]["conflict_risk"]
        directions = {
            signal["direction"] for signal in result["signals"]
            if signal["signal_id"] in risk_signal_ids
        }
        self.assertTrue({"increase", "decrease", "context_dependent"} <= directions)

    def test_tampered_brightness_is_rejected(self):
        resources = deepcopy(self.resources)
        resources["experiment"]["cases"][0]["stars"][0]["brightness"] = "陷"
        with self.assertRaisesRegex(ResearchConfigError, "亮度应为利"):
            _validate_resources(resources)

    def test_model_version_mismatch_is_rejected(self):
        resources = deepcopy(self.resources)
        resources["experiment"]["model_versions"]["star_interactions"] = "9.9.9"
        with self.assertRaisesRegex(ResearchConfigError, "模型版本不一致"):
            _validate_resources(resources)


if __name__ == "__main__":
    unittest.main()
