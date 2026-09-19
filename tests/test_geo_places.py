"""G1a 地名解析内核测试（出生地点交互优化方案 §10 测试清单）。

覆盖：zoneinfo 推导（中国夏令时全期、1942-1945、:30/:45 偏移、负夏令时、LMT）、
检索、软校验触发与不触发、curated 数据自动校验与配额。
"""
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))

import geo_places as geo  # noqa: E402


INDEX = geo.load_places()


class CuratedDataTests(unittest.TestCase):
    def test_count_and_groups_match_quota(self):
        meta = INDEX.meta()
        self.assertEqual(meta["count"], 300)
        self.assertEqual(meta["revision"], INDEX.revision)
        self.assertEqual(
            meta["groups"],
            {"cn_core": 34, "cn_extra": 120, "tw_hk_mo": 20, "world_cap": 100, "world_ext": 26},
        )

    def test_ids_are_unique_and_prefixed(self):
        ids = [place["id"] for place in INDEX.places]
        self.assertEqual(len(ids), len(set(ids)))
        for place_id in ids:
            self.assertTrue(place_id.startswith("curated:"))
        self.assertIn("curated:cn-shanghai", INDEX.by_id)

    def test_shanghai_coordinates_equal_old_page_defaults(self):
        # 方案 §4.2 连续性：默认案例坐标取同一组值，改造前后排盘完全相同
        place = INDEX.by_id["curated:cn-shanghai"]
        self.assertEqual(place["lat"], 31.2304)
        self.assertEqual(place["lon"], 121.4737)
        self.assertEqual(place["tz"], "Asia/Shanghai")

    def test_every_tz_loads_in_zoneinfo(self):
        for place in INDEX.places:
            self.assertIsNotNone(geo._zone(place["tz"]), msg=f"时区不可加载：{place['id']}")

    def test_longitude_consistent_with_standard_offset(self):
        # 方案 §6.1：|lon − S/15| ≤ 30°（含 180° 折回），抓符号写反/坐标对调
        probe = datetime(2026, 1, 15, 12)
        for place in INDEX.places:
            info = geo.offset_info(place["tz"], probe)
            self.assertIsNotNone(info, msg=place["id"])
            expected_meridian = info["std_offset_minutes"] / 60 * 15
            diff = abs(geo._wrap180(expected_meridian - place["lon"]))
            self.assertLessEqual(
                diff, 30.0,
                msg=f"{place['id']} 经度 {place['lon']} 与时区标准经线 {expected_meridian} 差 {diff:.1f}°",
            )

    def test_required_fields_and_ranges(self):
        for place in INDEX.places:
            self.assertTrue(-90 <= place["lat"] <= 90)
            self.assertTrue(-180 <= place["lon"] <= 180)
            self.assertGreater(place["approx_radius_km"], 0)
            self.assertIn(place["level"], {"city"})
            self.assertTrue(place["aliases"])
            self.assertEqual(place["source"], "curated")
            self.assertEqual(place["revision"], INDEX.revision)


class TimezoneDerivationTests(unittest.TestCase):
    def shanghai(self, year, month, day, hour=14):
        return geo.offset_info("Asia/Shanghai", datetime(year, month, day, hour))

    def test_default_case_hits_1986_1991_dst(self):
        # 方案 §1.2：1990-05-20 上海当时实际是 UTC+9（540）
        info = self.shanghai(1990, 5, 20)
        self.assertEqual(info["utc_offset_minutes"], 540)
        self.assertEqual(info["std_offset_minutes"], 480)
        self.assertEqual(info["dst_minutes"], 60)
        self.assertTrue(info["dst_active"])

    def test_all_china_dst_era_sums_active_summer_winter_standard(self):
        for year in range(1986, 1992):
            summer = self.shanghai(year, 7, 1)
            self.assertEqual(summer["utc_offset_minutes"], 540, msg=f"{year} 年夏季应为 UTC+9")
            self.assertTrue(summer["dst_active"], msg=year)
            winter = self.shanghai(year, 1, 15)
            self.assertEqual(winter["utc_offset_minutes"], 480, msg=f"{year} 年冬季应为 UTC+8")
            self.assertFalse(winter["dst_active"], msg=year)

    def test_1942_1945_continuous_utc9_not_dst_labelled(self):
        # 方案 §1.2：1942-02-01 至 1945-09-01 连续三年半 UTC+9
        for (year, month) in [(1942, 3), (1943, 6), (1944, 12), (1945, 6)]:
            self.assertEqual(self.shanghai(year, month, 15)["utc_offset_minutes"], 540,
                             msg=f"{year}-{month}")
        self.assertEqual(self.shanghai(1941, 6, 15)["utc_offset_minutes"], 540)  # 1941 DST 段

    def test_post_1991_pure_standard_time(self):
        info = self.shanghai(1994, 12, 8)
        self.assertEqual(info["utc_offset_minutes"], 480)
        self.assertFalse(info["dst_active"])

    def test_half_and_quarter_hour_offsets(self):
        kolkata = geo.offset_info("Asia/Kolkata", datetime(1990, 5, 20, 12))
        self.assertEqual(kolkata["utc_offset_minutes"], 330)
        self.assertEqual(kolkata["std_offset_minutes"], 330)
        self.assertEqual(kolkata["dst_minutes"], 0)
        kathmandu = geo.offset_info("Asia/Kathmandu", datetime(1990, 5, 20, 12))
        self.assertEqual(kathmandu["utc_offset_minutes"], 345)

    def test_negative_dst_dublin_winter(self):
        # 方案 §5.4：A=0, S=60, DST=−60（tzdata 把爱尔兰标准时定为 UTC+1）
        info = geo.offset_info("Europe/Dublin", datetime(2020, 1, 15, 12))
        self.assertEqual(info["utc_offset_minutes"], 0)
        self.assertEqual(info["std_offset_minutes"], 60)
        self.assertEqual(info["dst_minutes"], -60)
        self.assertFalse(info["dst_active"])

    def test_negative_dst_casablanca_ramadan(self):
        info = geo.offset_info("Africa/Casablanca", datetime(2024, 3, 15, 12))
        self.assertEqual(info["utc_offset_minutes"], 0)
        self.assertEqual(info["std_offset_minutes"], 60)
        self.assertEqual(info["dst_minutes"], -60)

    def test_dst_transition_window_brackets_birth_and_expresses_resume(self):
        # 方案 §4.2：止日写成「…为止、恢复日为切换次日」，不把切换日当夏令时结束日
        idx = INDEX
        resolution = geo.resolve_place(
            idx, place_id="curated:cn-shanghai",
            birth_date={"year": 1990, "month": 5, "day": 20, "hour": 14},
        )
        window = resolution["time"]["dst_transition"]
        self.assertIsNotNone(window)
        self.assertLessEqual(window["start"], "1990-05-20")
        self.assertLessEqual("1990-05-20", window["end"])
        self.assertEqual(
            (datetime.strptime(window["resume"], "%Y-%m-%d")
             - datetime.strptime(window["end"], "%Y-%m-%d")).days, 1,
        )
        self.assertLess(window["start"], window["end"])

    def test_lmt_era_is_data_driven_and_uncertain(self):
        idx = INDEX
        self.assertTrue(geo.is_lmt_era("Asia/Shanghai", datetime(1890, 6, 1).date()))
        self.assertFalse(geo.is_lmt_era("Asia/Shanghai", datetime(1950, 1, 1).date()))
        resolution = geo.resolve_place(
            idx, place_id="curated:cn-shanghai",
            birth_date={"year": 1890, "month": 6, "day": 1},
        )
        self.assertEqual(resolution["time"]["confidence"], "uncertain")
        codes = [warning["code"] for warning in resolution["warnings"]]
        self.assertIn("lmt_uncertain", codes)
        # LMT 段偏移取整分钟（±8:05:43 → 485/486），误差 ≤30s 在文案里承认
        self.assertIn(resolution["time"]["utc_offset_minutes"], (485, 486))


class SearchTests(unittest.TestCase):
    def test_chinese_substring_and_prefix(self):
        hits = geo.search_places(INDEX, "上海")
        self.assertEqual(hits[0]["id"], "curated:cn-shanghai")
        hits = geo.search_places(INDEX, "南")
        ids = [hit["id"] for hit in hits]
        for expected in ["curated:cn-nanjing", "curated:cn-nanchang",
                         "curated:cn-nanning", "curated:cn-nanyang", "curated:cn-nantong"]:
            self.assertIn(expected, ids)

    def test_pinyin_full_and_initials_and_english(self):
        self.assertEqual(geo.search_places(INDEX, "shanghai")[0]["id"], "curated:cn-shanghai")
        self.assertEqual(geo.search_places(INDEX, "nanjing")[0]["id"], "curated:cn-nanjing")
        self.assertEqual(geo.search_places(INDEX, "shaoxing")[0]["id"], "curated:cn-shaoxing")
        self.assertEqual(geo.search_places(INDEX, "nj")[0]["id"], "curated:cn-nanjing")
        self.assertEqual(geo.search_places(INDEX, "wlmq")[0]["id"], "curated:cn-urumqi")
        self.assertEqual(geo.search_places(INDEX, "beijing")[0]["id"], "curated:cn-beijing")

    def test_one_cjk_char_triggers_but_one_ascii_char_does_not(self):
        # 方案 §4.1：中文 1 个字即可触发；拼音/英文需 2 个字符
        self.assertTrue(geo.search_places(INDEX, "常"))
        self.assertEqual(geo.search_places(INDEX, "s"), [])

    def test_prefix_beats_substring(self):
        hits = geo.search_places(INDEX, "昌")
        # 昌都市（前缀命中，§6.3 权重大于子串命中）应排在南昌/许昌（子串命中）之前
        self.assertEqual(hits[0]["id"], "curated:cn-chamdo")
        ids = [hit["id"] for hit in hits]
        self.assertIn("curated:cn-nanchang", ids)
        self.assertLess(ids.index("curated:cn-chamdo"), ids.index("curated:cn-nanchang"))
        # 拼音/英文只做前缀匹配，不做子串匹配
        self.assertEqual(geo.search_places(INDEX, "anghai"), [])
        scored = [hit["score"] for hit in geo.search_places(INDEX, "sh")]
        self.assertEqual(scored, sorted(scored, reverse=True))

    def test_no_match_returns_empty(self):
        self.assertEqual(geo.search_places(INDEX, "不存在的城市xyzabc"), [])

    def test_limit_bounds_and_country_filter(self):
        self.assertEqual(len(geo.search_places(INDEX, "市", limit=5)), 5)
        with self.assertRaises(geo.GeoInvalidRequest):
            geo.search_places(INDEX, "上海", limit=51)
        with self.assertRaises(geo.GeoInvalidRequest):
            geo.search_places(INDEX, "上海", limit=0)
        hits = geo.search_places(INDEX, "shanghai", country="CN")
        self.assertTrue(all(hit["country_code"] == "CN" for hit in hits))

    def test_overlong_query_rejected(self):
        with self.assertRaises(geo.GeoInvalidRequest):
            geo.search_places(INDEX, "上" * 65)


class ResolveTests(unittest.TestCase):
    def test_place_id_resolution_structure(self):
        resolution = geo.resolve_place(
            INDEX, place_id="curated:cn-shanghai",
            birth_date={"year": 1990, "month": 5, "day": 20, "hour": 14},
        )
        self.assertEqual(resolution["place"]["id"], "curated:cn-shanghai")
        self.assertEqual(resolution["place"]["display"], "上海市")
        self.assertEqual(resolution["time"]["utc_offset_minutes"], 540)
        self.assertEqual(resolution["time"]["tz_name"], "Asia/Shanghai")
        self.assertEqual(resolution["time"]["confidence"], "city")
        self.assertTrue(resolution["time"]["tz_available"])
        self.assertEqual(resolution["provenance"]["rule"], "zoneinfo:Asia/Shanghai")
        self.assertEqual(resolution["provenance"]["dataset"], "curated")
        self.assertIn("tzdata_version", resolution["provenance"])
        self.assertEqual(resolution["location"], {"latitude": 31.2304, "longitude": 121.4737})
        self.assertIsInstance(resolution["warnings"], list)

    def test_query_resolution_and_not_found(self):
        resolution = geo.resolve_place(
            INDEX, query="杭州", birth_date={"year": 2000, "month": 1, "day": 1},
        )
        self.assertEqual(resolution["place"]["id"], "curated:cn-hangzhou")
        with self.assertRaises(geo.GeoNotFoundError):
            geo.resolve_place(INDEX, query="不存在的地方名xyz",
                              birth_date={"year": 2000, "month": 1, "day": 1})
        with self.assertRaises(geo.GeoNotFoundError):
            geo.resolve_place(INDEX, place_id="curated:no-such",
                              birth_date={"year": 2000, "month": 1, "day": 1})

    def test_coordinate_path_keeps_user_coords_and_marks_approximate(self):
        # 未解析态（§4.7）：反查最近城市仅作提示，place.display 带「约：」
        resolution = geo.resolve_place(
            INDEX, lat=31.2, lon=121.4,
            birth_date={"year": 1990, "month": 5, "day": 20},
            utc_offset_minutes=480,
        )
        self.assertEqual(resolution["location"], {"latitude": 31.2, "longitude": 121.4})
        self.assertEqual(resolution["provenance"]["derived_from"], "nearest")
        self.assertEqual(resolution["time"]["confidence"], "approximate")
        self.assertTrue(resolution["place"]["display"].startswith("约："))
        codes = [warning["code"] for warning in resolution["warnings"]]
        # 用户填的 480 与夏令时推导的 540 矛盾 → dst_not_applied（§4.6 规则 4）
        self.assertIn("dst_not_applied", codes)

    def test_coordinate_far_from_any_place_has_no_place_but_full_blocks(self):
        resolution = geo.resolve_place(
            INDEX, lat=-30.0, lon=-160.0, birth_date={"year": 2000, "month": 1, "day": 1},
        )
        self.assertIsNone(resolution["place"])
        self.assertIsNone(resolution["time"]["utc_offset_minutes"])
        self.assertIsNotNone(resolution["provenance"])
        self.assertIsInstance(resolution["warnings"], list)

    def test_mutually_exclusive_inputs(self):
        with self.assertRaises(geo.GeoInvalidRequest):
            geo.resolve_place(INDEX, place_id="curated:cn-shanghai", lat=1.0, lon=2.0,
                              birth_date={"year": 2000, "month": 1, "day": 1})
        with self.assertRaises(geo.GeoInvalidRequest):
            geo.resolve_place(INDEX, birth_date={"year": 2000, "month": 1, "day": 1})
        with self.assertRaises(geo.GeoInvalidRequest):
            geo.resolve_place(INDEX, place_id="curated:cn-shanghai", birth_date={"year": 1700, "month": 1, "day": 1})
        with self.assertRaises(geo.GeoInvalidRequest):
            geo.resolve_place(INDEX, place_id="curated:cn-shanghai", birth_date={"year": 2000, "month": 2, "day": 30})
        with self.assertRaises(geo.GeoInvalidRequest):
            geo.resolve_place(INDEX, place_id="curated:cn-shanghai", lat=95.0, lon=0.0,
                              birth_date={"year": 2000, "month": 1, "day": 1})


class ConsistencyCheckTests(unittest.TestCase):
    def shanghai_1990_info(self):
        return geo.offset_info("Asia/Shanghai", datetime(1990, 5, 20, 14))

    def test_offset_longitude_mismatch_fires_and_not(self):
        warnings = geo.check_location_consistency(utc_offset_minutes=0, lat=31.2, lon=121.4)
        self.assertIn("offset_longitude_mismatch", [w["code"] for w in warnings])
        # 正确口径不触发
        warnings = geo.check_location_consistency(utc_offset_minutes=540, lat=31.2, lon=121.4)
        self.assertNotIn("offset_longitude_mismatch", [w["code"] for w in warnings])
        # 跨 180° 折回：Apia UTC+13 / 171.8°W 不误报
        warnings = geo.check_location_consistency(utc_offset_minutes=780, lat=-13.83, lon=-171.77)
        self.assertNotIn("offset_longitude_mismatch", [w["code"] for w in warnings])

    def test_near_zero_coordinates(self):
        warnings = geo.check_location_consistency(utc_offset_minutes=0, lat=0.2, lon=0.3)
        self.assertIn("near_zero_coordinates", [w["code"] for w in warnings])
        warnings = geo.check_location_consistency(utc_offset_minutes=0, lat=0.6, lon=0.3)
        self.assertNotIn("near_zero_coordinates", [w["code"] for w in warnings])

    def test_polar_placidus_only_with_placidus(self):
        warnings = geo.check_location_consistency(lat=78.0, lon=15.0, house_system="placidus")
        self.assertIn("polar_placidus", [w["code"] for w in warnings])
        warnings = geo.check_location_consistency(lat=78.0, lon=15.0, house_system="whole_sign")
        self.assertNotIn("polar_placidus", [w["code"] for w in warnings])
        warnings = geo.check_location_consistency(lat=50.0, lon=15.0, house_system="placidus")
        self.assertNotIn("polar_placidus", [w["code"] for w in warnings])

    def test_dst_not_applied_when_user_reverts_to_standard(self):
        info = self.shanghai_1990_info()
        warnings = geo.check_location_consistency(
            utc_offset_minutes=480, lat=31.2, lon=121.4, auto_info=info)
        self.assertIn("dst_not_applied", [w["code"] for w in warnings])
        warnings = geo.check_location_consistency(
            utc_offset_minutes=540, lat=31.2, lon=121.4, auto_info=info)
        self.assertNotIn("dst_not_applied", [w["code"] for w in warnings])

    def test_city_level_radius_notice_only_for_large(self):
        warnings = geo.check_location_consistency(lat=29.5, lon=106.5, approx_radius_km=150)
        self.assertIn("city_level_radius", [w["code"] for w in warnings])
        warnings = geo.check_location_consistency(lat=31.2, lon=121.4, approx_radius_km=30)
        self.assertNotIn("city_level_radius", [w["code"] for w in warnings])
        # 重庆作为 >50km 的真实样例在解析里出现提示
        resolution = geo.resolve_place(
            INDEX, place_id="curated:cn-chongqing", birth_date={"year": 1994, "month": 12, "day": 8})
        self.assertIn("city_level_radius", [w["code"] for w in resolution["warnings"]])


class IndexLoadingTests(unittest.TestCase):
    def test_missing_data_directory_raises_config_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(geo.GeoConfigError):
                geo.load_places(tmp)

    def test_checksum_mismatch_raises_config_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            (tmp / "curated.json").write_text("[]", encoding="utf-8")
            (tmp / "index.json").write_text(
                '{"revision":"x","shards":{"curated":{"sha256":"deadbeef"}}}', encoding="utf-8")
            with self.assertRaises(geo.GeoConfigError):
                geo.load_places(tmp)

    def test_geo_meta_shape(self):
        meta = geo.geo_meta(INDEX)
        self.assertEqual(meta["count"], 300)
        self.assertEqual(meta["revision"], INDEX.revision)
        self.assertTrue(meta["tz_available"])
        self.assertTrue(meta["tzdata_version"])
        self.assertIn("tz_path", meta)


if __name__ == "__main__":
    unittest.main()
