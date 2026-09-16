import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "build" / "examples" / "astro_web_cli"
EPHEMERIS = ROOT / "data" / "ephemeris"


REQUEST = {
    "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
    "utc_offset_minutes": 480,
    "location": {"latitude": 31.2304, "longitude": 121.4737},
    "allow_moshier_fallback": False,
    "include_aspects": False,
}


@unittest.skipUnless(CLI.exists(), "astro_web_cli has not been built")
class AstroWebContractTests(unittest.TestCase):
    def run_cli(self, request, ephemeris_path=None):
        env = os.environ.copy()
        env["ZHOUYILAB_EPHEMERIS_PATH"] = str(ephemeris_path or EPHEMERIS)
        completed = subprocess.run(
            [str(CLI)],
            input=json.dumps(request),
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        return completed.returncode, json.loads(completed.stdout)

    def test_high_precision_uses_bundled_ephemeris(self):
        code, payload = self.run_cli(REQUEST)
        self.assertEqual(code, 0)
        self.assertEqual(payload["calculation"]["precision_mode"], "high")
        self.assertEqual(payload["calculation"]["ephemeris"], "swiss")
        self.assertEqual(payload["calculation"]["warnings"], [])
        self.assertEqual(len(payload["planets"]), 12)
        self.assertIn("chiron", {planet["id"] for planet in payload["planets"]})

    def test_structured_payload_is_machine_parseable(self):
        code, payload = self.run_cli(REQUEST)
        self.assertEqual(code, 0)
        structured = payload["structured"]
        self.assertEqual(structured["schema_version"], "astro-structured/1.0")
        self.assertEqual(structured["coordinate_frame"], "geocentric_apparent")
        self.assertEqual(len(structured["points"]), len(payload["planets"]))
        sun = next(point for point in structured["points"] if point["id"] == "sun")
        self.assertEqual(sun["kind"], "celestial_point")
        self.assertIn(sun["classification"]["element"], {"fire", "earth", "air", "water"})
        self.assertIn(sun["motion"]["direction"], {"direct", "retrograde"})
        self.assertEqual(set(structured["aggregates"]["element_counts"]), {"fire", "earth", "air", "water"})
        derived = structured["derived_signals"]
        self.assertEqual(derived["schema_version"], "astro-derived-signals/1.0")
        self.assertTrue(derived["signals"])
        for signal in derived["signals"]:
            self.assertIn("signal_id", signal)
            self.assertIn("type", signal)
            self.assertIn("point_ids", signal)
            self.assertIn("evidence", signal)

    def test_meta_exposes_structured_schema_version(self):
        code, payload = self.run_cli({"operation": "meta"})
        self.assertEqual(code, 0)
        self.assertEqual(payload["structured_schema_version"], "astro-structured/1.0")
        self.assertEqual(payload["derived_signals_schema_version"], "astro-derived-signals/1.0")

    def test_missing_ephemeris_is_rejected_without_fallback(self):
        with tempfile.TemporaryDirectory() as path:
            code, payload = self.run_cli(REQUEST, path)
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["error"]["code"], "EPHEMERIS_UNAVAILABLE")

    def test_missing_ephemeris_can_use_explicit_moshier_fallback(self):
        request = {**REQUEST, "allow_moshier_fallback": True}
        with tempfile.TemporaryDirectory() as path:
            code, payload = self.run_cli(request, path)
        self.assertEqual(code, 0)
        self.assertEqual(payload["calculation"]["precision_mode"], "moshier")
        self.assertIn("使用了 Moshier 降级模式", payload["calculation"]["warnings"])
        self.assertNotIn("chiron", {planet["id"] for planet in payload["planets"]})
        self.assertIn("Moshier 模式不支持凯龙星，已跳过 chiron", payload["calculation"]["warnings"])


class AstroWebSourceContractTests(unittest.TestCase):
    def test_server_defaults_engine_to_project_ephemeris_directory(self):
        source = (ROOT / "web" / "server.py").read_text(encoding="utf-8")
        self.assertIn('"ZHOUYILAB_EPHEMERIS_PATH"', source)
        self.assertIn('PROJECT_ROOT / "data" / "ephemeris"', source)

    def test_prompt_copy_panel_is_present(self):
        html = (ROOT / "web" / "astro.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "astro.js").read_text(encoding="utf-8")
        self.assertIn('id="astro-prompt-text"', html)
        self.assertIn('id="astro-copy-prompt"', html)
        self.assertIn("buildAstroPrompt", script)
        self.assertIn("navigator.clipboard", script)
        self.assertIn("/api/v1/astro/analysis", script)


if __name__ == "__main__":
    unittest.main()
