import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTML = (PROJECT_ROOT / "web" / "qimen.html").read_text(encoding="utf-8")
JAVASCRIPT = (PROJECT_ROOT / "web" / "qimen.js").read_text(encoding="utf-8")
LEARNING_RULES = (PROJECT_ROOT / "web" / "qimen_learning.js").read_text(encoding="utf-8")


class QiMenWebContractTests(unittest.TestCase):
    def test_question_types_and_result_views_are_available(self):
        question_select = re.search(
            r'<select id="question-type">(.*?)</select>', HTML, flags=re.DOTALL,
        ).group(1)
        option_values = set(re.findall(r'<option value="([^"]+)">', question_select))

        self.assertEqual(
            {"general", "career", "relationship", "wealth", "travel"},
            option_values,
        )
        self.assertIn('id="board-tab"', HTML)
        self.assertIn('id="reading-tab"', HTML)
        self.assertIn('id="clues-tab"', HTML)
        self.assertIn('id="help-dialog"', HTML)
        self.assertIn('id="subject-birth-date"', HTML)
        self.assertIn('id="counterpart-birth-date"', HTML)
        self.assertNotIn('id="subject-stem"', HTML)
        self.assertNotIn('id="counterpart-stem"', HTML)

    def test_all_palaces_have_learning_metadata(self):
        palace_entries = re.findall(
            r"^\s{2}([1-9]): \{ element: '([^']+)', direction: '([^']+)', branches:",
            JAVASCRIPT,
            flags=re.MULTILINE,
        )

        if not palace_entries:
            palace_entries = re.findall(
                r"^\s{4}([1-9]): \{ element: '([^']+)', direction: '([^']+)', branches:",
                LEARNING_RULES,
                flags=re.MULTILINE,
            )

        self.assertEqual(set(range(1, 10)), {int(item[0]) for item in palace_entries})
        self.assertEqual(
            {"水", "土", "木", "金", "火"},
            {item[1] for item in palace_entries},
        )

    def test_ai_material_separates_fact_inference_and_advice(self):
        self.assertIn("【所问事项】", JAVASCRIPT)
        self.assertIn("【本次取用重点】", JAVASCRIPT)
        self.assertIn("盘面事实", JAVASCRIPT)
        self.assertIn("象意推断", JAVASCRIPT)
        self.assertIn("现实建议", JAVASCRIPT)
        self.assertIn("日旬空", JAVASCRIPT)
        self.assertIn("palace?.palace_num !== 5", JAVASCRIPT)
        self.assertIn("candidate.palace_num === 2", JAVASCRIPT)
        self.assertIn("【宫位关系线索】", JAVASCRIPT)
        self.assertIn("【特殊状态】", JAVASCRIPT)
        self.assertIn('id="pattern-list"', HTML)
        self.assertIn("buildSpecialStates", JAVASCRIPT)
        self.assertIn("六仪击刑", HTML)
        self.assertIn("三奇入墓", HTML)
        self.assertIn("五不遇时", HTML)
        self.assertIn("十干克应", HTML)
        self.assertIn("getStemResponse", JAVASCRIPT)
        self.assertIn("resolveLifeStem", JAVASCRIPT)
        self.assertIn("甲遁", JAVASCRIPT)
        self.assertIn('data-short="应"', JAVASCRIPT)
        self.assertIn("sourcePalace.palace_num === 5", JAVASCRIPT)
        self.assertLess(
            HTML.index('/qimen_learning.js'), HTML.index('/qimen.js'),
        )


if __name__ == "__main__":
    unittest.main()
