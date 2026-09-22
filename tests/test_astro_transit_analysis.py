import copy
import json
import unittest
from pathlib import Path

from web.astro_transit_analysis import (
    AstroTransitAnalysisConfigError,
    AstroTransitAnalysisRequestError,
    analyze_transit,
    load_rules,
)


ROOT = Path(__file__).resolve().parent.parent


def transit_facts():
    return {
        "chart_type": "transit",
        "structured": {
            "schema_version": "astro-transit-structured/1.0",
            "natal": {"schema_version": "astro-structured/1.0"},
            "transit_points": [],
            "aspects": [],
        },
        "transit": {
            "planets": [
                {"id": "venus", "natal_house": 2, "longitude": 214.0, "sign": "scorpio"},
                {"id": "mars", "natal_house": 10, "longitude": 113.4, "sign": "cancer"},
                {"id": "mercury", "natal_house": 3, "longitude": 190.5, "sign": "libra"},
                {"id": "moon", "natal_house": 7, "longitude": 245.7, "sign": "sagittarius"},
            ]
        },
        "aspects": [
            {
                "transit_point": "mars",
                "natal_point": "venus",
                "type": "square",
                "orb": 2.4,
                "phase": "applying",
                "actual_angle": 92.4,
            },
            {
                "transit_point": "mars",
                "natal_point": "moon",
                "type": "opposition",
                "orb": 5.2,
                "phase": "separating",
                "actual_angle": 174.8,
            },
            {
                "transit_point": "mars",
                "natal_point": "mercury",
                "type": "trine",
                "orb": 1.1,
                "phase": "applying",
                "actual_angle": 118.9,
            },
        ],
    }


class AstroTransitAnalysisTests(unittest.TestCase):
    def test_config_is_versioned_and_contains_all_dimensions(self):
        rules = load_rules()
        self.assertEqual(rules["schema_version"], "astro-transit-rules/1.0")
        self.assertTrue({rule["dimension"] for rule in rules["rules"]} ==
                        {"love", "wealth", "career", "learning", "social"})

    def test_house_and_aspect_signals_keep_fact_evidence(self):
        facts = transit_facts()
        packet = analyze_transit(facts)
        self.assertEqual(packet["analysis_version"], "astro-transit-analysis/1.0")
        self.assertEqual(packet["input_kind"], "astro_transit_structured_facts")
        self.assertEqual(packet["rules_version"], "astro-transit-rules/1.0")
        self.assertTrue(packet["signals"])
        by_code = {signal["observation_code"]: signal for signal in packet["signals"]}
        self.assertEqual(by_code["venus_activates_personal_resources"]["evidence"]["natal_house"], 2)
        self.assertEqual(by_code["mars_tension_with_natal_venus"]["evidence"]["aspect"]["orb"], 2.4)
        self.assertEqual(by_code["mars_tension_with_natal_moon"]["point_ids"], ["mars", "moon"])
        for signal in packet["signals"]:
            self.assertTrue({
                "signal_id", "rule_id", "revision", "dimension", "direction",
                "intensity", "observation_code", "point_ids", "evidence", "boundary",
            } <= set(signal))
        self.assertEqual(packet["source_schema_versions"], {
            "transit": "astro-transit-structured/1.0",
            "natal": "astro-structured/1.0",
        })

    def test_dimensions_filter_and_index_are_consistent(self):
        packet = analyze_transit(transit_facts(), dimensions=["career", "love"])
        self.assertEqual(list(packet["dimensions"]), ["career", "love"])
        self.assertTrue(packet["dimensions"]["career"]["signals"])
        self.assertTrue(packet["dimensions"]["love"]["signals"])
        self.assertEqual(
            {signal["signal_id"] for signal in packet["signals"]},
            {signal["signal_id"] for item in packet["dimensions"].values()
             for signal in item["signals"]},
        )
        serialized = json.dumps(packet, ensure_ascii=False)
        for forbidden in ("summary", "actions", "avoid", "lucky", "score", "index"):
            self.assertNotIn(forbidden, serialized)

    def test_scope_alias_and_invalid_dimensions(self):
        self.assertEqual(
            analyze_transit(transit_facts(), scope=["social"])["dimensions"].keys(),
            {"social"},
        )
        with self.assertRaises(AstroTransitAnalysisRequestError):
            analyze_transit(transit_facts(), dimensions=["health"])
        with self.assertRaises(AstroTransitAnalysisRequestError):
            analyze_transit(transit_facts(), scope=["love"], dimensions=["career"])

    def test_invalid_fact_package_is_rejected(self):
        invalid = copy.deepcopy(transit_facts())
        invalid["structured"]["schema_version"] = "astro-structured/1.0"
        with self.assertRaises(AstroTransitAnalysisRequestError):
            analyze_transit(invalid)

    def test_invalid_rule_configuration_is_rejected(self):
        rules = load_rules()
        rules["rules"][0] = {"rule_id": "broken"}
        with self.assertRaises(AstroTransitAnalysisConfigError):
            analyze_transit(transit_facts(), rules=rules)


if __name__ == "__main__":
    unittest.main()
