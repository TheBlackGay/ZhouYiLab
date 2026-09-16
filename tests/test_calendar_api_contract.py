import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CALENDAR_MODULE = (ROOT / "src/common/calendar/calendar.cppm").read_text()
CLI = (ROOT / "examples/common_calendar_web_cli.cpp").read_text()
SERVER = (ROOT / "web/server.py").read_text()
DOC = (ROOT / "docs/common/公共日历API.md").read_text()
CMAKE = (ROOT / "examples/CMakeLists.txt").read_text()
BUILD_SCRIPT = (ROOT / "build.sh").read_text()


class CalendarApiContractTest(unittest.TestCase):
    def test_public_cpp_api_is_declared(self):
        for name in (
            "solar_to_lunar",
            "lunar_to_solar",
            "correct_solar_time",
            "calculate_true_solar_time",
            "calculate_equation_of_time_seconds",
        ):
            self.assertIn(name, CALENDAR_MODULE)

    def test_json_cli_exposes_both_operations(self):
        self.assertIn('operation == "convert"', CLI)
        self.assertIn('operation == "true_solar_time"', CLI)
        self.assertIn('"leap_month"', CLI)
        self.assertIn('"true_solar_time"', CLI)

    def test_http_routes_use_the_common_cli(self):
        self.assertIn('"/api/v1/calendar/convert": "calendar_convert"', SERVER)
        self.assertIn('"/api/v1/calendar/true-solar-time": "calendar_true_solar_time"', SERVER)
        self.assertIn("CALENDAR_CLI_PATH", SERVER)
        self.assertIn("common_calendar_web_cli", CMAKE)
        self.assertIn("common_calendar_web_cli", BUILD_SCRIPT)

    def test_public_api_documentation_covers_cpp_and_http(self):
        self.assertIn("ZhouYi.Common.Calendar", DOC)
        self.assertIn("POST /api/v1/calendar/convert", DOC)
        self.assertIn("POST /api/v1/calendar/true-solar-time", DOC)


if __name__ == "__main__":
    unittest.main()
