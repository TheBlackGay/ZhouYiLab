import copy
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "web"))

from ziwei_brightness import (  # noqa: E402
    apply_star_brightness,
    apply_transit_star_brightness,
    load_brightness_config,
    normalize_brightness_response,
)


class ZiWeiBrightnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_brightness_config()

    def make_chart(self):
        palaces = []
        branches = self.config["branches"]
        for branch in branches:
            palaces.append({
                "gan_zhi": f"甲{branch}",
                "zhu_xing": [],
                "fu_xing_detail": [],
                "sha_xing_detail": [],
                "za_yao_detail": [],
            })
        return {"palaces": palaces}

    def test_table_is_complete_and_valid(self):
        self.assertEqual(12, len(self.config["branches"]))
        self.assertGreaterEqual(len(self.config["stars"]), 60)
        self.assertTrue(all(len(values) == 12 for values in self.config["stars"].values()))

    def test_real_brightness_overwrites_placeholder(self):
        chart = self.make_chart()
        chart["palaces"][0]["fu_xing_detail"] = [
            {"name": "左辅", "liang_du": "平"},
            {"name": "禄存", "liang_du": "平"},
        ]
        chart["palaces"][1]["sha_xing_detail"] = [
            {"name": "擎羊", "liang_du": "平"},
        ]
        chart["palaces"][6]["sha_xing_detail"] = [
            {"name": "铃星", "liang_du": "平"},
        ]
        chart["palaces"][6]["za_yao_detail"] = [
            {"name": "天马", "liang_du": "平"},
        ]

        apply_star_brightness(chart, self.config)

        self.assertEqual("庙", chart["palaces"][0]["fu_xing_detail"][0]["liang_du"])
        self.assertEqual("庙", chart["palaces"][0]["fu_xing_detail"][1]["liang_du"])
        self.assertEqual("陷", chart["palaces"][1]["sha_xing_detail"][0]["liang_du"])
        self.assertEqual("陷", chart["palaces"][6]["sha_xing_detail"][0]["liang_du"])
        self.assertEqual("旺", chart["palaces"][6]["za_yao_detail"][0]["liang_du"])

    def test_blank_and_dash_cells_remove_fake_brightness(self):
        chart = self.make_chart()
        chart["palaces"][0]["fu_xing_detail"] = [
            {"name": "天魁", "liang_du": "平"},
        ]
        chart["palaces"][0]["za_yao_detail"] = [
            {"name": "台辅", "liang_du": "平"},
        ]

        apply_star_brightness(chart, self.config)

        self.assertNotIn("liang_du", chart["palaces"][0]["fu_xing_detail"][0])
        self.assertNotIn("liang_du", chart["palaces"][0]["za_yao_detail"][0])

    def test_aliases_and_nested_response_are_supported(self):
        chart = self.make_chart()
        chart["palaces"][3]["sha_xing_detail"] = [{"name": "火星"}]
        chart["palaces"][3]["za_yao_detail"] = [{"name": "截路"}]
        response = {"chart": copy.deepcopy(chart)}

        normalize_brightness_response(response)

        self.assertEqual("得", response["chart"]["palaces"][3]["sha_xing_detail"][0]["liang_du"])
        self.assertEqual("庙", response["chart"]["palaces"][3]["za_yao_detail"][0]["liang_du"])
        self.assertEqual("1.0.0", response["chart"]["brightness_table_version"])

    def test_transit_stars_use_base_name_and_physical_palace(self):
        chart = self.make_chart()
        response = {
            "chart": chart,
            "fortune": {
                "liu_ri": {
                    "transit_stars": [
                        {"name": "天喜", "display_name": "日喜", "palace_index": 1},
                        {"name": "台辅", "display_name": "日辅", "palace_index": 0,
                         "liang_du": "平"},
                    ]
                }
            },
        }

        apply_transit_star_brightness(response, self.config)

        stars = response["fortune"]["liu_ri"]["transit_stars"]
        self.assertEqual("旺", stars[0]["liang_du"])
        self.assertNotIn("liang_du", stars[1])


if __name__ == "__main__":
    unittest.main()
