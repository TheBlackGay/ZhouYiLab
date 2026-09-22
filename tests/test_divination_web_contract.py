import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class DivinationWebContractTests(unittest.TestCase):
    def test_pages_expose_inputs_and_shared_navigation(self):
        for name, form_id, title in (
            ("liu-yao.html", "liu-yao-form", "六爻"),
            ("da-liu-ren.html", "da-liu-ren-form", "大六壬"),
        ):
            html = (ROOT / "web" / name).read_text(encoding="utf-8")
            self.assertIn(f'id="{form_id}"', html)
            self.assertIn(title, html)
            self.assertIn('href="/liu-yao.html"', html)
            self.assertIn('href="/da-liu-ren.html"', html)

    def test_cli_contracts_return_core_fields(self):
        cases = (
            ("liu_yao_web_cli", {"calendar": "solar", "date": {"year": 2025, "month": 4, "day": 7, "hour": 17}, "hexagram_code": "110001", "changing_lines": [1]}, "yao"),
            ("da_liu_ren_web_cli", {"calendar": "solar", "date": {"year": 2025, "month": 11, "day": 3, "hour": 16}}, "san_chuan"),
        )
        for binary, request, field in cases:
            path = ROOT / "build" / "examples" / binary
            if not path.exists():
                self.skipTest(f"{binary} 尚未构建")
            completed = subprocess.run([str(path)], input=json.dumps(request), text=True, capture_output=True, check=True)
            payload = json.loads(completed.stdout)
            self.assertIn(field, payload)
            if binary == "da_liu_ren_web_cli":
                self.assertEqual(len(payload["tian_di_pan"]), 12)
                self.assertTrue(all("position" in item and "tian_pan" in item for item in payload["tian_di_pan"]))
                self.assertEqual(len(payload["san_chuan"]["details"]), 3)
                self.assertIn("gua_ti", payload)
            if binary == "liu_yao_web_cli":
                self.assertTrue(all(item["mainYaoType"] in {"0", "1"} for item in payload["yao"]))


if __name__ == "__main__":
    unittest.main()
