import json
import os
import subprocess
import unittest
from pathlib import Path

from web.astro_analysis import AstroAnalysisRequestError, analyze_natal_chart, load_rules


ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "build" / "examples" / "astro_web_cli"


@unittest.skipUnless(CLI.exists(), "astro_web_cli has not been built")
class AstroAnalysisTests(unittest.TestCase):
    def chart(self):
        request = {
            "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
            "utc_offset_minutes": 480,
            "location": {"latitude": 31.2304, "longitude": 121.4737},
            "include_aspects": True,
        }
        env = os.environ.copy()
        env["ZHOUYILAB_EPHEMERIS_PATH"] = str(ROOT / "data" / "ephemeris")
        result = subprocess.run([str(CLI)], input=json.dumps(request), text=True,
                                capture_output=True, env=env, cwd=ROOT, check=True)
        return json.loads(result.stdout)

    def test_analysis_packet_groups_evidence(self):
        packet = analyze_natal_chart(self.chart())
        self.assertEqual(packet["analysis_version"], "astro-analysis/1.0")
        self.assertEqual(packet["input_kind"], "astro_natal_structured_signals")
        self.assertIn("core_points", packet["sections"])
        self.assertIn("signals", packet["sections"])
        self.assertTrue(packet["sections"]["signals"]["by_type"])
        self.assertEqual(packet["rules_version"], "astro-rules/1.0")
        self.assertTrue(packet["observations"])
        self.assertTrue(all(item["rule_id"].startswith("struct.") for item in packet["observations"]))

    def test_scope_limits_sections(self):
        packet = analyze_natal_chart(self.chart(), ["distribution", "aspect_network"])
        self.assertEqual(packet["section_order"], ["distribution", "aspect_network"])
        self.assertNotIn("signals", packet["sections"])

    def test_invalid_scope_is_rejected(self):
        with self.assertRaises(AstroAnalysisRequestError):
            analyze_natal_chart(self.chart(), ["interpretation"])

    def test_rules_are_configured_and_validated(self):
        rules = load_rules()
        self.assertEqual(rules["schema_version"], "astro-rules/1.0")
        self.assertGreaterEqual(len(rules["rules"]), 5)


if __name__ == "__main__":
    unittest.main()
