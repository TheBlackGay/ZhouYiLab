import copy
import json
import unittest

from web.astro_daily_reading import (
    AstroDailyReadingConfigError,
    AstroDailyReadingRequestError,
    analyze_and_render,
    load_templates,
    render_daily_reading,
)
from web.astro_transit_analysis import analyze_transit


def facts():
    return {
        "chart_type": "transit",
        "input": {
            "target": {
                "date": {"year": 2026, "month": 9, "day": 17, "hour": 12}
            }
        },
        "structured": {
            "schema_version": "astro-transit-structured/1.0",
            "natal": {"schema_version": "astro-structured/1.0"},
        },
        "transit": {
            "planets": [
                {"id": "venus", "natal_house": 2, "longitude": 214.0},
                {"id": "mars", "natal_house": 10, "longitude": 113.4},
            ]
        },
        "aspects": [
            {
                "transit_point": "mars",
                "natal_point": "venus",
                "type": "square",
                "orb": 2.4,
                "phase": "applying",
            }
        ],
    }


class AstroDailyReadingTests(unittest.TestCase):
    def test_templates_cover_all_configured_signals(self):
        templates = load_templates()
        analysis = analyze_transit(facts())
        configured = set(templates["signals"])
        self.assertEqual(
            {signal["rule_id"] for signal in analysis["signals"]},
            {"wealth.venus_in_houses_2_8", "career.sun_or_mars_in_house_6_or_10", "love.mars_hard_aspect_natal_venus"},
        )
        self.assertTrue(configured)

    def test_daily_packet_is_score_free_and_traceable(self):
        packet = analyze_and_render(facts())
        self.assertEqual(packet["date"], "2026-09-17")
        self.assertEqual(packet["scope"], "day")
        self.assertEqual(packet["versions"]["reading_schema"], "astro-daily-reading/1.0")
        self.assertEqual(packet["versions"]["templates"], "astro-daily-templates/1.0")
        self.assertIsNone(packet["overall"]["index"])
        self.assertEqual(packet["focus"]["dimension"], "love")
        self.assertTrue(packet["summary"])
        self.assertTrue(packet["actions"])
        self.assertTrue(packet["avoid"])
        self.assertEqual(
            {item["signal_id"] for item in packet["evidence"]},
            set(packet["overall"]["signal_ids"]),
        )
        for dimension in packet["dimensions"].values():
            self.assertIsNone(dimension["index"])
        serialized = json.dumps(packet, ensure_ascii=False)
        self.assertNotIn('"score"', serialized)
        self.assertNotIn('"probability"', serialized)

    def test_empty_day_has_explicit_empty_state(self):
        empty = copy.deepcopy(facts())
        empty["transit"]["planets"] = []
        empty["aspects"] = []
        packet = analyze_and_render(empty, dimensions=["learning"])
        self.assertEqual(packet["dimensions"]["learning"]["signal_ids"], [])
        self.assertEqual(packet["focus"]["dimension"], None)
        self.assertEqual(packet["actions"], [])
        self.assertEqual(packet["avoid"], [])
        self.assertEqual(packet["evidence"], [])

    def test_render_accepts_existing_analysis_packet(self):
        analysis = analyze_transit(facts(), dimensions=["wealth"])
        packet = render_daily_reading(analysis, requested_date="2026-09-18")
        self.assertEqual(packet["date"], "2026-09-18")
        self.assertEqual(packet["dimensions"]["wealth"]["signal_ids"], [
            "wealth.venus_in_houses_2_8:venus"
        ])
        self.assertEqual(packet["dimensions"]["love"]["signal_ids"], [])

    def test_invalid_date_and_analysis_are_rejected(self):
        with self.assertRaises(AstroDailyReadingRequestError):
            analyze_and_render(facts(), requested_date="2026-02-30")
        with self.assertRaises(AstroDailyReadingRequestError):
            render_daily_reading({"analysis_version": "astro-analysis/1.0"})

    def test_missing_signal_template_is_rejected(self):
        analysis = analyze_transit(facts())
        templates = load_templates()
        del templates["signals"][analysis["signals"][0]["rule_id"]]
        with self.assertRaises(AstroDailyReadingConfigError):
            render_daily_reading(analysis, templates=templates)


if __name__ == "__main__":
    unittest.main()
