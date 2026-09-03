import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIMENSION_PATH = (
    PROJECT_ROOT / "config" / "ziwei" / "research" / "dimension_dictionary.json"
)
STAR_PROFILE_PATH = (
    PROJECT_ROOT / "config" / "ziwei" / "research" / "star_energy_profiles.json"
)
INTERACTION_PATH = (
    PROJECT_ROOT / "config" / "ziwei" / "research" / "star_interactions.json"
)
EXPERIMENT_PATH = (
    PROJECT_ROOT / "config" / "ziwei" / "research" / "experiments"
    / "lianzhen_qisha_v0.1.json"
)
BLIND_PROTOCOL_PATH = (
    PROJECT_ROOT / "config" / "ziwei" / "research" / "blind_review_protocol.json"
)


class ZiWeiResearchConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dictionary = json.loads(DIMENSION_PATH.read_text(encoding="utf-8"))
        cls.star_profiles = json.loads(STAR_PROFILE_PATH.read_text(encoding="utf-8"))
        cls.interactions = json.loads(INTERACTION_PATH.read_text(encoding="utf-8"))
        cls.experiment = json.loads(EXPERIMENT_PATH.read_text(encoding="utf-8"))
        cls.blind_protocol = json.loads(
            BLIND_PROTOCOL_PATH.read_text(encoding="utf-8")
        )

    def test_pilot_dimension_dictionary_contract(self):
        payload = self.dictionary
        self.assertEqual("1.0.0", payload["schema_version"])
        self.assertEqual("frozen_for_pilot", payload["status"])
        self.assertTrue(payload["decision_record"])
        self.assertEqual(-1.0, payload["scale"]["minimum"])
        self.assertEqual(1.0, payload["scale"]["maximum"])
        self.assertEqual(0.1, payload["scale"]["precision"])

        dimensions = payload["dimensions"]
        ids = [item["id"] for item in dimensions]
        self.assertEqual(11, len(ids))
        self.assertEqual(len(ids), len(set(ids)))

        required_fields = {
            "id", "name", "definition", "positive_direction",
            "negative_direction", "includes", "excludes",
            "evidence_level", "parameter_status",
        }
        for dimension in dimensions:
            with self.subTest(dimension=dimension["id"]):
                self.assertTrue(required_fields <= dimension.keys())
                self.assertTrue(dimension["includes"])
                self.assertTrue(dimension["excludes"])
                self.assertEqual("E5", dimension["evidence_level"])
                self.assertEqual("reviewed", dimension["parameter_status"])

    def test_mixed_constructs_are_split_for_pilot(self):
        ids = {item["id"] for item in self.dictionary["dimensions"]}
        self.assertTrue({
            "authority_influence", "execution_action",
            "cognition_planning", "communication_expression",
            "emotional_intensity", "desire_drive",
        } <= ids)
        self.assertTrue({
            "authority_execution", "learning_expression", "emotion_desire",
        }.isdisjoint(ids))

    def test_lianzhen_qisha_profiles_are_qualitative_and_traceable(self):
        payload = self.star_profiles
        self.assertEqual("qualitative_only", payload["status"])
        self.assertEqual(
            self.dictionary["dictionary_version"],
            payload["dimension_dictionary_version"],
        )
        self.assertEqual({"lianzhen", "qisha"}, {
            item["id"] for item in payload["stars"]
        })

        dimension_ids = {item["id"] for item in self.dictionary["dimensions"]}
        source_ids = {item["id"] for item in payload["sources"]}
        mechanism_ids = set()
        for star_profile in payload["stars"]:
            with self.subTest(star=star_profile["id"]):
                self.assertTrue(set(star_profile["attributes"]["source_refs"]) <= source_ids)
                self.assertTrue(star_profile["unresolved_questions"])
                for mechanism in star_profile["mechanisms"]:
                    self.assertNotIn(mechanism["id"], mechanism_ids)
                    mechanism_ids.add(mechanism["id"])
                    self.assertTrue(set(mechanism["source_refs"]) <= source_ids)
                    for hypothesis in mechanism["dimension_hypotheses"]:
                        self.assertIn(hypothesis["dimension_id"], dimension_ids)
                        self.assertIn(hypothesis["direction"], {
                            "increase", "decrease", "context_dependent"
                        })
                        self.assertEqual("E5", hypothesis["evidence_level"])
                        self.assertEqual("proposed", hypothesis["parameter_status"])

    def test_star_profiles_do_not_contain_unvalidated_numeric_parameters(self):
        forbidden_keys = {"weight", "score", "coefficient", "delta", "base_vector"}

        def visit(value):
            if isinstance(value, dict):
                self.assertTrue(forbidden_keys.isdisjoint(value.keys()))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(self.star_profiles)

    def test_lianzhen_qisha_interaction_contract(self):
        payload = self.interactions
        self.assertEqual("qualitative_only", payload["status"])
        self.assertEqual("preserve_all_signals", payload["combination_policy"]["mode"])
        self.assertEqual(
            self.dictionary["dictionary_version"],
            payload["dimension_dictionary_version"],
        )
        self.assertEqual(
            self.star_profiles["catalog_version"],
            payload["star_profile_catalog_version"],
        )

        interaction = payload["interactions"][0]
        self.assertEqual(
            "interaction.lianzhen_controls_qisha.same_palace", interaction["id"]
        )
        self.assertEqual("same_palace", interaction["required_context"]["relation"])
        self.assertTrue(interaction["required_context"]["same_source_layer"])
        self.assertEqual("controls", interaction["elemental_mechanism"]["relation"])
        self.assertEqual({"lianzhen", "qisha"}, {
            item["star_id"] for item in interaction["participants"]
        })

        modifier_ids = {item["id"] for item in interaction["modifiers"]}
        self.assertEqual({
            "core_brightness_supported", "same_layer_hualu_support",
            "same_layer_huaquan_support", "lianzhen_huaji",
        }, modifier_ids)

    def test_interaction_references_known_dimensions_stars_and_sources(self):
        dimension_ids = {item["id"] for item in self.dictionary["dimensions"]}
        star_ids = {item["id"] for item in self.star_profiles["stars"]}
        source_ids = {item["id"] for item in self.interactions["sources"]}

        for interaction in self.interactions["interactions"]:
            self.assertTrue({
                item["star_id"] for item in interaction["participants"]
            } <= star_ids)
            self.assertTrue(set(interaction["source_refs"]) <= source_ids)
            hypotheses = list(interaction["base_hypotheses"])
            for modifier in interaction["modifiers"]:
                self.assertTrue(set(modifier["source_refs"]) <= source_ids)
                hypotheses.extend(modifier["hypotheses"])
                targets = set(modifier["trigger"].get("target_star_ids", []))
                self.assertTrue(targets <= star_ids)
                self.assertEqual("$current_layer", modifier["trigger"]["source_layer"])
            for hypothesis in hypotheses:
                self.assertIn(hypothesis["dimension_id"], dimension_ids)
                self.assertEqual("E5", hypothesis["evidence_level"])
                self.assertEqual("proposed", hypothesis["parameter_status"])

    def test_interactions_do_not_contain_unvalidated_numeric_parameters(self):
        forbidden_keys = {"weight", "score", "coefficient", "delta", "base_vector"}

        def visit(value):
            if isinstance(value, dict):
                self.assertTrue(forbidden_keys.isdisjoint(value.keys()))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(self.interactions)

    def test_pilot_experiment_declares_minimal_fixture_boundary(self):
        payload = self.experiment
        self.assertEqual("frozen_for_pilot", payload["status"])
        self.assertEqual(
            "minimal_local_context", payload["fixture_policy"]["completeness"]
        )
        self.assertEqual(8, len(payload["cases"]))
        controlled = [
            signal
            for case in payload["cases"]
            for signal in case["transformation_signals"]
        ]
        self.assertTrue(controlled)
        self.assertTrue(all(
            signal["fact_status"] == "controlled_stimulus" and signal["boundary"]
            for signal in controlled
        ))

    def test_blind_review_protocol_is_frozen_before_collection(self):
        protocol = self.blind_protocol
        self.assertEqual("frozen_before_collection", protocol["status"])
        self.assertEqual(
            self.experiment["experiment_version"], protocol["experiment_version"]
        )
        self.assertEqual(
            self.dictionary["dictionary_version"],
            protocol["dimension_dictionary_version"],
        )
        self.assertEqual(3, protocol["rater_plan"]["minimum_raters"])
        self.assertEqual(5, protocol["rater_plan"]["target_raters"])
        self.assertEqual(
            [-1.0, -0.5, 0.0, 0.5, 1.0],
            protocol["rating_scale"]["allowed_values"],
        )
        self.assertLess(
            protocol["agreement"]["thresholds"]["provisional_acceptance"],
            protocol["agreement"]["thresholds"]["strong_agreement"],
        )


if __name__ == "__main__":
    unittest.main()
