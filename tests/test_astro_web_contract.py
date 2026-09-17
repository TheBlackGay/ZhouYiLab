import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "build" / "examples" / "astro_web_cli"
EPHEMERIS = ROOT / "data" / "ephemeris"
TRANSIT_FIXTURE = ROOT / "tests" / "fixtures" / "astro_transit_1990-05-20_to_2026-09-17.json"


REQUEST = {
    "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
    "utc_offset_minutes": 480,
    "location": {"latitude": 31.2304, "longitude": 121.4737},
    "allow_moshier_fallback": False,
    "include_aspects": False,
}

TRANSIT_REQUEST = {
    "natal": REQUEST,
    "target": {"date": {"year": 2026, "month": 9, "day": 17, "hour": 12}},
    "allow_moshier_fallback": False,
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

    def test_transit_fact_packet_is_stable_and_uses_natal_houses(self):
        code, payload = self.run_cli({"operation": "transit", **TRANSIT_REQUEST})
        self.assertEqual(code, 0)
        self.assertEqual(payload["chart_type"], "transit")
        self.assertEqual(payload["structured"]["schema_version"], "astro-transit-structured/1.0")
        self.assertEqual(payload["calculation"]["precision_mode"], "high")
        self.assertEqual(
            {planet["id"] for planet in payload["transit"]["planets"]},
            {"sun", "moon", "mercury", "venus", "mars"},
        )
        self.assertTrue(all(1 <= planet["natal_house"] <= 12 for planet in payload["transit"]["planets"]))
        self.assertTrue(payload["aspects"])
        self.assertTrue(all({"transit_point", "natal_point", "type", "orb", "phase"} <= set(aspect) for aspect in payload["aspects"]))

    def test_transit_fixture_values(self):
        fixture = json.loads(TRANSIT_FIXTURE.read_text(encoding="utf-8"))
        code, payload = self.run_cli({"operation": "transit", **fixture["request"]})
        self.assertEqual(code, 0)
        expected = fixture["expected"]
        self.assertEqual(payload["structured"]["schema_version"], expected["schema_version"])
        self.assertEqual(payload["calculation"]["precision_mode"], expected["precision_mode"])
        self.assertAlmostEqual(payload["calculation"]["natal_julian_day_ut"], expected["natal_julian_day_ut"], places=8)
        self.assertAlmostEqual(payload["calculation"]["transit_julian_day_ut"], expected["transit_julian_day_ut"], places=8)
        by_id = {planet["id"]: planet for planet in payload["transit"]["planets"]}
        for point_id, longitude in expected["transit_longitudes"].items():
            self.assertAlmostEqual(by_id[point_id]["longitude"], longitude, places=8)
            self.assertEqual(by_id[point_id]["natal_house"], expected["natal_houses"][point_id])

    def test_transit_target_inherits_natal_location_and_time_zone(self):
        code, payload = self.run_cli({"operation": "transit", **TRANSIT_REQUEST})
        self.assertEqual(code, 0)
        target = payload["input"]["target"]
        self.assertEqual(target["utc_offset_minutes"], 480)
        self.assertEqual(target["latitude"], 31.2304)
        self.assertEqual(target["longitude"], 121.4737)

    def test_transit_rejects_mismatched_zodiac(self):
        request = {
            **TRANSIT_REQUEST,
            "target": {**TRANSIT_REQUEST["target"], "zodiac": "sidereal", "ayanamsa": "fagan_bradley"},
        }
        code, payload = self.run_cli({"operation": "transit", **request})
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["error"]["code"], "INVALID_REQUEST")

    def test_transit_accepts_all_natal_angle_points(self):
        request = {
            **TRANSIT_REQUEST,
            "natal_points": ["midheaven", "descendant", "imum_coeli"],
            "transit_points": ["sun"],
        }
        code, payload = self.run_cli({"operation": "transit", **request})
        self.assertEqual(code, 0)
        self.assertEqual(payload["input"]["natal_points"], request["natal_points"])
        self.assertEqual(len(payload["transit"]["planets"]), 1)

    def test_transit_missing_ephemeris_respects_explicit_fallback(self):
        with tempfile.TemporaryDirectory() as path:
            code, payload = self.run_cli(
                {"operation": "transit", **{**TRANSIT_REQUEST, "allow_moshier_fallback": True}}, path
            )
        self.assertEqual(code, 0)
        self.assertEqual(payload["calculation"]["precision_mode"], "moshier")
        self.assertIn("使用了 Moshier 降级模式", payload["calculation"]["warnings"])


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

    def test_transit_route_and_schema_are_exposed(self):
        server = (ROOT / "web" / "server.py").read_text(encoding="utf-8")
        controller = (ROOT / "src" / "astro" / "astro_controller.cppm").read_text(encoding="utf-8")
        cli = (ROOT / "examples" / "astro_web_cli.cpp").read_text(encoding="utf-8")
        self.assertIn('"/api/v1/astro/transits"', server)
        self.assertIn("astro-transit-structured/1.0", controller)
        self.assertIn('operation == "transit"', cli)

    def test_transit_analysis_route_and_rules_are_exposed(self):
        server = (ROOT / "web" / "server.py").read_text(encoding="utf-8")
        analysis = (ROOT / "web" / "astro_transit_analysis.py").read_text(encoding="utf-8")
        rules = (ROOT / "config" / "astro" / "transit_rules.json").read_text(encoding="utf-8")
        self.assertIn('"/api/v1/astro/transit-analysis"', server)
        self.assertIn("run_astro_transit_analysis", server)
        self.assertIn('"astro-transit-analysis/1.0"', analysis)
        self.assertIn('"astro-transit-rules/1.0"', rules)
        for dimension in ("love", "wealth", "career", "learning", "social"):
            self.assertIn(f'"dimension": "{dimension}"', rules)

    def test_daily_reading_route_and_schema_are_exposed(self):
        server = (ROOT / "web" / "server.py").read_text(encoding="utf-8")
        reading = (ROOT / "web" / "astro_daily_reading.py").read_text(encoding="utf-8")
        templates = (ROOT / "config" / "astro" / "daily_reading_templates.json").read_text(encoding="utf-8")
        self.assertIn('"/api/v1/astro/daily-reading"', server)
        self.assertIn("run_astro_daily_reading", server)
        self.assertIn('"astro-daily-reading/1.0"', reading)
        self.assertIn('"astro-daily-templates/1.0"', templates)
        self.assertIn("summary", reading)
        self.assertIn("avoid", reading)

    def test_astro_page_uses_shared_workspace_shell(self):
        html = (ROOT / "web" / "astro.html").read_text(encoding="utf-8")
        for fragment in (
            'class="skip-link"', 'class="app-navigation"', 'class="secondary-bar"',
            'class="workspace astro-workspace"', 'class="input-panel"',
            'class="results"', 'class="result-summary"', 'id="astro-chart-tab"',
        ):
            self.assertIn(fragment, html)

    def test_astro_page_loads_shared_workspace_baseline(self):
        html = (ROOT / "web" / "astro.html").read_text(encoding="utf-8")
        css = (ROOT / "web" / "astro.css").read_text(encoding="utf-8")
        # The shared shell class names only render as the 320px sidebar workspace
        # when the shared baseline (form, input-panel, results, result-summary)
        # is loaded, and page styles must be applied before the app shell.
        self.assertIn("@import url('/qimen.css')", css)
        self.assertLess(
            html.index('href="/ui-foundation.css"'),
            html.index('href="/astro.css"'),
        )
        self.assertLess(
            html.index('href="/astro.css"'),
            html.index('href="/app-shell.css"'),
        )

    def test_astro_wheel_has_layered_rings_and_orientation_control(self):
        html = (ROOT / "web" / "astro.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "astro.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "astro.css").read_text(encoding="utf-8")
        for fragment in (
            'data-orientation="ascendant"', 'data-orientation="aries"',
            'id="astro-wheel-legend"', 'viewBox="0 0 640 640"',
        ):
            self.assertIn(fragment, html)
        # 星座环必须是圆环扇形（annulus），不能是从圆心铺满整盘的整块楔形。
        self.assertIn("function annulus(", script)
        self.assertIn("annulus(WHEEL.cx, WHEEL.cy, WHEEL.rim, WHEEL.signInner, mid)", script)
        for fragment in ("element-", "mode-", "axis-label", "planet-degree", "spreadLabels", "dotRadii"):
            self.assertIn(fragment, script)
        for fragment in (
            ".sign-sector.element-fire", ".mode-sector.mode-cardinal",
            ".planet-degree", ".wheel-legend", ".axis-label",
        ):
            self.assertIn(fragment, css)

    def test_astro_wheel_orders_zodiac_counterclockwise(self):
        script = (ROOT / "web" / "astro.js").read_text(encoding="utf-8")
        # 标准西洋星盘：黄经逆时针排列。上升点在左时上升黄经映射到屏幕 270°，
        # 因此屏幕角为 base - 黄经；白羊在顶时 base 为 0。
        self.assertIn("(Number(data.angles?.ascendant ?? 0) + 270) % 360", script)
        self.assertIn("const screen = longitude => ((base - Number(longitude)) % 360 + 360) % 360;", script)

    def test_natal_layout_analysis_and_reading_are_exposed(self):
        server = (ROOT / "web" / "server.py").read_text(encoding="utf-8")
        analysis = (ROOT / "web" / "astro_natal_analysis.py").read_text(encoding="utf-8")
        reading = (ROOT / "web" / "astro_natal_reading.py").read_text(encoding="utf-8")
        rules = (ROOT / "config" / "astro" / "natal_rules.json").read_text(encoding="utf-8")
        templates = (ROOT / "config" / "astro" / "natal_reading_templates.json").read_text(encoding="utf-8")
        self.assertIn('"/api/v1/astro/natal-analysis"', server)
        self.assertIn('"/api/v1/astro/natal-reading"', server)
        self.assertIn("run_astro_natal_analysis", server)
        self.assertIn("run_astro_natal_reading", server)
        self.assertIn('"astro-natal-analysis/1.0"', analysis)
        self.assertIn('"astro-natal-reading/1.0"', reading)
        self.assertIn('"astro-natal-rules/1.0"', rules)
        self.assertIn('"astro-natal-templates/1.0"', templates)
        # 布局统计口径必须显式回传，且与规则层解耦。
        for fragment in ("hemisphere_stat", "quadrant_stat", "empty_house", "aspect_network_stat",
                         "counted_point_ids", "DISTRIBUTION_POINTS"):
            self.assertIn(fragment, analysis)
        # 只统计十大行星，虚点不参与分布统计。
        self.assertIn("DISTRIBUTION_POINTS = (", analysis)
        self.assertNotIn('"true_node"', analysis)
        self.assertNotIn('"chiron"', analysis)

    def test_astro_reading_tab_and_layout_bars_are_present(self):
        html = (ROOT / "web" / "astro.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "astro.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "astro.css").read_text(encoding="utf-8")
        for fragment in (
            'id="astro-reading-tab"', 'id="astro-reading-panel"', 'id="astro-core-row"',
            'id="astro-layout-bars"', 'id="astro-layout-notes"', 'id="astro-layout-defs"',
            'id="astro-wheel-highlight"', 'id="astro-reading-empty"',
        ):
            self.assertIn(fragment, html)
        for fragment in ("/api/v1/astro/natal-reading", "layoutBar", "highlightWheelHouses",
                         "house-sector", "clearLayoutSelection"):
            self.assertIn(fragment, script)
        for fragment in (".layout-bar-seg", ".house-sector.on", ".astro-core-row",
                         ".layout-note-meta", ".wheel-highlight-note"):
            self.assertIn(fragment, css)


if __name__ == "__main__":
    unittest.main()
