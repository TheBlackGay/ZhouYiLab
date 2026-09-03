import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "web"))

from ziwei_ai_review import (  # noqa: E402
    AiReviewProviderError,
    AiReviewService,
    build_case_prompt,
    load_ai_review_protocol,
    redacted_provider,
    summarize_dimension_rows,
    validate_model_ratings,
    validate_provider,
)


class ZiWeiAiReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.provider_path = Path(self.temp.name) / "providers.json"
        self.provider_path.write_text(json.dumps({
            "config_version": "0.1.0",
            "providers": [{**self.provider(), "enabled": True}],
        }, ensure_ascii=False), encoding="utf-8")
        self.service = AiReviewService(
            Path(self.temp.name) / "ai-review.sqlite3", self.provider_path
        )
        self.packet = self.service.packet("pilot-2026")

    def tearDown(self):
        self.temp.cleanup()

    def provider(self, repetitions=1):
        return {
            "provider_id": "local-qwen",
            "label": "本地 Qwen",
            "protocol": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": "qwen3:8b",
            "model_family": "Qwen3",
            "api_key": "must-not-be-persisted",
            "temperature": 0,
            "repetitions": repetitions,
            "model_seed": 42,
        }

    def valid_response(self, score=0.5):
        return json.dumps({
            "ratings": [{
                "dimension_id": dimension["id"],
                "score": score,
                "rationale": "基于匿名星曜事实作出的独立方向判断。",
            } for dimension in self.packet["dimensions"]]
        }, ensure_ascii=False)

    def test_protocol_forbids_treating_model_runs_as_human_evidence(self):
        protocol = load_ai_review_protocol()
        boundary = protocol["interpretation_boundary"]
        self.assertTrue(boundary["model_runs_are_not_human_raters"])
        self.assertTrue(boundary["repeated_runs_are_not_independent_experts"])
        self.assertTrue(boundary["agreement_is_descriptive_only"])
        self.assertFalse(boundary["may_create_numeric_star_weights"])
        self.assertFalse(protocol["data_policy"]["persist_api_keys"])

    def test_prompt_is_blind_and_contains_frozen_dimensions(self):
        prompt = build_case_prompt(
            self.packet, self.packet["cases"][0], self.service.protocol
        )
        self.assertIn("resource_mobilization", prompt)
        self.assertIn("不要猜测格局名称", prompt)
        for hidden in ("answer_key", "LQ-A", "雄宿乾元", "expected"):
            self.assertNotIn(hidden, prompt)

    def test_provider_validation_and_redaction_never_return_secret(self):
        provider = validate_provider(self.provider(), self.service.protocol)
        self.assertEqual("Qwen3", provider["model_family"])
        redacted = redacted_provider(provider)
        self.assertNotIn("api_key", redacted)
        self.assertTrue(redacted["has_api_key"])
        self.assertNotIn("must-not-be-persisted", json.dumps(redacted))

    def test_model_response_requires_exact_dimension_set(self):
        value = json.loads(self.valid_response())
        value["ratings"][1]["dimension_id"] = value["ratings"][0]["dimension_id"]
        with self.assertRaisesRegex(AiReviewProviderError, "维度集合"):
            validate_model_ratings(value, self.packet)

    def test_background_experiment_persists_runs_and_descriptive_summary(self):
        response = self.valid_response()
        with patch("ziwei_ai_review.call_model", return_value=(response, {
            "input_tokens": 120, "output_tokens": 80
        })):
            experiment = self.service.create_experiment({
                "seed": "pilot-2026",
                "provider_ids": ["local-qwen"],
                "overrides": {"local-qwen": {"repetitions": 2}},
            })
            with self.service._lock:
                thread = self.service._threads[experiment["id"]]
            thread.join(timeout=5)
        stored = self.service.store.get_experiment(experiment["id"])
        self.assertEqual("completed", stored["status"])
        self.assertEqual(16, stored["completed_tasks"])
        self.assertEqual(0, stored["failed_tasks"])
        self.assertNotIn("must-not-be-persisted", json.dumps(stored))
        result = self.service.results(experiment["id"])
        self.assertEqual("AI 多模型定性预评审", result["report_label"])
        self.assertEqual(16, len(result["runs"]))
        self.assertEqual("0.2.0", result["results_schema_version"])
        self.assertTrue(all(
            item["direction_prevalence_ratio"] == 1.0
            and item["within_case_cross_model_agreement"] is None
            and item["cross_model_descriptive_consensus_ratio"] is None
            and item["interpretation"] == "within_case_descriptive_only_not_human_agreement"
            for item in result["dimensions"]
        ))
        self.assertEqual(1.0, result["provider_stability"][0]["mean_exact_pair_agreement"])
        self.assertFalse(result["interpretation_boundary"]["may_create_numeric_star_weights"])

    def test_cross_model_agreement_compares_models_within_matching_case(self):
        rows = []
        directions = {
            "case-a": {"model-a": [1, 1, 1], "model-b": [-1], "model-c": [-1]},
            "case-b": {"model-a": [1, 1, 1], "model-b": [1], "model-c": [-1]},
        }
        for case_code, providers in directions.items():
            for provider_id, scores in providers.items():
                rows.extend({
                    "provider_id": provider_id,
                    "case_code": case_code,
                    "score": score,
                } for score in scores)

        summary = summarize_dimension_rows(rows)

        self.assertEqual(6, summary["model_case_count"])
        self.assertEqual(0.5, summary["direction_prevalence_ratio"])
        self.assertEqual(0.6667, summary["within_case_cross_model_agreement"])
        self.assertEqual(0, summary["unanimous_case_count"])
        self.assertEqual(2, summary["comparable_case_count"])
        self.assertEqual(0.3333, summary["pairwise_direction_agreement"])
        self.assertEqual(6, summary["comparable_model_pairs"])

    def test_invalid_model_output_is_retried_and_recorded_as_failure(self):
        with patch("ziwei_ai_review.call_model", return_value=("not-json", {})) as mocked:
            experiment = self.service.create_experiment({
                "provider_ids": ["local-qwen"],
            })
            with self.service._lock:
                thread = self.service._threads[experiment["id"]]
            thread.join(timeout=5)
        stored = self.service.store.get_experiment(experiment["id"])
        self.assertEqual("completed_with_errors", stored["status"])
        self.assertEqual(8, stored["failed_tasks"])
        self.assertEqual(24, mocked.call_count)


if __name__ == "__main__":
    unittest.main()
