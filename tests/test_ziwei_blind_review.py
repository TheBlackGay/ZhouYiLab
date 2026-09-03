import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "web"))

from ziwei_blind_review import (  # noqa: E402
    analyze_submissions,
    generate_blind_packet,
    krippendorff_alpha_interval,
    load_blind_review_resources,
)
from ziwei_research_engine import ResearchConfigError  # noqa: E402


class ZiWeiBlindReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources, cls.protocol = load_blind_review_resources()

    def test_packet_is_deterministic_and_hides_model_answers(self):
        first, first_key = generate_blind_packet(
            self.resources, self.protocol, "pilot-seed"
        )
        second, second_key = generate_blind_packet(
            self.resources, self.protocol, "pilot-seed"
        )
        other, _ = generate_blind_packet(
            self.resources, self.protocol, "different-seed"
        )
        self.assertEqual(first, second)
        self.assertEqual(first_key, second_key)
        self.assertNotEqual(first["packet_id"], other["packet_id"])
        self.assertEqual(8, len(first["cases"]))
        self.assertEqual(11, len(first["dimensions"]))

        serialized = json.dumps(first, ensure_ascii=False)
        for hidden in (
            "LQ-A", "LQ-B", "雄宿乾元", "expected", "purpose",
            "interaction.lianzhen_controls_qisha",
        ):
            self.assertNotIn(hidden, serialized)
        self.assertNotIn("answer_key", first)
        for original_case_id in first_key.values():
            self.assertNotIn(original_case_id, serialized)

    def test_identical_raters_produce_strong_agreement(self):
        packet, _ = generate_blind_packet(
            self.resources, self.protocol, "agreement-seed"
        )
        scores = lambda case_index: -0.5 if case_index % 2 == 0 else 0.5
        submissions = [self._submission(packet, f"rater-{index}", scores)
                       for index in range(3)]
        result = analyze_submissions(packet, submissions, self.protocol)
        self.assertEqual(3, result["rater_count"])
        self.assertIsNone(result["overall_alpha"])
        self.assertTrue(all(
            item["alpha"] == 1.0 and item["status"] == "strong_agreement"
            for item in result["dimensions"]
        ))

    def test_systematic_disagreement_requires_revision(self):
        packet, _ = generate_blind_packet(
            self.resources, self.protocol, "disagreement-seed"
        )
        submissions = [
            self._submission(packet, "rater-negative", -1.0),
            self._submission(packet, "rater-neutral", 0.0),
            self._submission(packet, "rater-positive", 1.0),
        ]
        result = analyze_submissions(packet, submissions, self.protocol)
        self.assertTrue(all(
            item["status"] == "revision_required"
            for item in result["dimensions"]
        ))

    def test_invalid_score_and_duplicate_rater_are_rejected(self):
        packet, _ = generate_blind_packet(
            self.resources, self.protocol, "validation-seed"
        )
        submission = self._submission(packet, "rater-a", 0.5)
        invalid = deepcopy(submission)
        invalid["ratings"][0]["dimensions"][0]["score"] = 0.2
        with self.assertRaisesRegex(ResearchConfigError, "分值不在允许量尺"):
            analyze_submissions(
                packet, [invalid, self._submission(packet, "rater-b", 0.5),
                         self._submission(packet, "rater-c", 0.5)], self.protocol
            )
        with self.assertRaisesRegex(ResearchConfigError, "评分者 ID 重复"):
            analyze_submissions(packet, [submission, deepcopy(submission),
                                         self._submission(packet, "rater-c", 0.5)],
                                self.protocol)

    def test_interval_alpha_handles_missing_values(self):
        alpha = krippendorff_alpha_interval([
            [0.5, 0.5, 0.5],
            [1.0, 1.0],
            [],
        ])
        self.assertEqual(1.0, alpha)
        self.assertIsNone(krippendorff_alpha_interval([[0.5], [], [None]][:2]))
        self.assertIsNone(krippendorff_alpha_interval([[0.5, 0.5, 0.5]] * 3))

    def _submission(self, packet, rater_id, score):
        submission = deepcopy(packet["submission_template"])
        submission["rater_id"] = rater_id
        submission["rater_group"] = "pilot"
        for case_index, case in enumerate(submission["ratings"]):
            for dimension in case["dimensions"]:
                dimension["score"] = score(case_index) if callable(score) else score
                dimension["rationale"] = "独立盲评测试依据"
        return submission


if __name__ == "__main__":
    unittest.main()
