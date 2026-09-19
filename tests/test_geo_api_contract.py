"""G1a 中立解析接口契约测试（方案 §7 + §10 验收）。

在测试进程内起真实 HTTP 服务（不依赖 C++ 引擎），验证：
- GET  /api/v1/geo/places 的候选结构、参数越界、缺 q；
- POST /api/v1/geo/place-resolve 的 PlaceResolution 结构、404/400；
- GET  /api/v1/geo/meta 的 revision/count/tzdata_version/tz_available；
- GET  /api/v1/astro/meta 的 geo 扩展字段；
- 缺 data/geo/ 时返回 GEO_CONFIG_ERROR（降级不失效，§10 验收）。
"""
import json
import pathlib
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))

import geo_places  # noqa: E402
import server  # noqa: E402


class GeoApiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.ZhouYiHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    # ---- helpers ----------------------------------------------------------
    def request(self, path, body=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        if body is None:
            request = urllib.request.Request(url)
        else:
            request = urllib.request.Request(
                url,
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def get(self, path):
        return self.request(path)

    def post(self, body, path="/api/v1/geo/place-resolve"):
        return self.request(path, body=body)

    # ---- GET /api/v1/geo/places -------------------------------------------
    def test_places_success_envelope_and_hit_shape(self):
        status, payload = self.get("/api/v1/geo/places?q=%E4%B8%8A%E6%B5%B7")
        self.assertEqual(status, 200)
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(data["count"], len(data["results"]))
        self.assertEqual(data["results"][0]["id"], "curated:cn-shanghai")
        self.assertEqual(data["results"][0]["display"], "上海市")
        self.assertEqual(data["results"][0]["tz"], "Asia/Shanghai")
        self.assertEqual(data["results"][0]["lat"], 31.2304)
        self.assertEqual(data["results"][0]["lon"], 121.4737)
        self.assertEqual(data["revision"], geo_places.default_index().revision)
        # 统一响应信封（与既有 send_api_success 约定一致）
        self.assertEqual(payload["meta"]["api_version"], "v1")
        self.assertIn("request_id", payload["meta"])

    def test_places_rejects_missing_or_bad_params(self):
        def url(params):
            return "/api/v1/geo/places?" + urllib.parse.urlencode(params)
        cases = [
            "/api/v1/geo/places",                      # 缺 q
            url({"q": " "}),                           # 空白 q
            url({"q": "上" * 65}),                     # 超长 q
            url({"q": "上海", "limit": "0"}),          # limit 越界
            url({"q": "上海", "limit": "51"}),         # limit 上限外
            url({"q": "上海", "limit": "abc"}),        # limit 非整数
            url({"q": "上海", "country": "CHINA"}),    # country 非两位码
        ]
        for path in cases:
            status, payload = self.get(path)
            self.assertEqual(status, 400, msg=path)
            self.assertEqual(payload["error"]["code"], "INVALID_REQUEST", msg=path)

    def test_places_country_filter_and_empty_result_is_200(self):
        status, payload = self.get("/api/v1/geo/places?q=shanghai&country=JP")
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["results"], [])
        # 空结果不是 404：搜索无匹配由 GET 返回空列表，404 只属于 resolve 的 query 语义
        status, payload = self.get("/api/v1/geo/places?q=%E4%B8%8D%E5%AD%98%E5%9C%A8xyz")
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["count"], 0)

    # ---- POST /api/v1/geo/place-resolve ------------------------------------
    def test_resolve_place_id_1990_case_returns_dst_offset(self):
        status, payload = self.post({
            "place_id": "curated:cn-shanghai",
            "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
        })
        self.assertEqual(status, 200)
        data = payload["data"]
        self.assertEqual(data["time"]["utc_offset_minutes"], 540)
        self.assertEqual(data["time"]["std_offset_minutes"], 480)
        self.assertEqual(data["time"]["dst_minutes"], 60)
        self.assertTrue(data["time"]["dst_active"])
        self.assertEqual(data["time"]["tz_name"], "Asia/Shanghai")
        window = data["time"]["dst_transition"]
        self.assertLessEqual(window["start"], "1990-05-20")
        self.assertGreaterEqual(window["end"], "1990-05-20")
        self.assertEqual(data["provenance"]["dataset"], "curated")
        self.assertEqual(data["provenance"]["rule"], "zoneinfo:Asia/Shanghai")
        self.assertTrue(data["provenance"]["tzdata_version"])

    def test_resolve_structure_is_always_complete(self):
        status, payload = self.post({
            "latitude": 31.2, "longitude": 121.4,
            "date": {"year": 1990, "month": 5, "day": 20},
            "utc_offset_minutes": 480,
            "house_system": "placidus",
        })
        self.assertEqual(status, 200)
        data = payload["data"]
        for key in ("place", "location", "time", "provenance", "warnings"):
            self.assertIn(key, data)
        self.assertEqual(data["location"], {"latitude": 31.2, "longitude": 121.4})
        self.assertTrue(data["place"]["display"].startswith("约："))
        codes = [warning["code"] for warning in data["warnings"]]
        self.assertIn("dst_not_applied", codes)

    def test_resolve_404_and_400_paths(self):
        status, payload = self.post({
            "query": "不存在的地方xyz", "date": {"year": 1990, "month": 5, "day": 20},
        })
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"]["code"], "PLACE_NOT_FOUND")

        status, payload = self.post({
            "place_id": "curated:cn-nowhere", "date": {"year": 1990, "month": 5, "day": 20},
        })
        self.assertEqual(status, 404)

        bad_bodies = [
            {"date": {"year": 1990, "month": 5, "day": 20}},                  # 无地点输入
            {"place_id": "curated:cn-shanghai"},                              # 缺 date
            {"place_id": "curated:cn-shanghai",
             "date": {"year": 1990, "month": 2, "day": 30}},                  # 非法日期
            {"place_id": "curated:cn-shanghai", "query": "上海",
             "date": {"year": 1990, "month": 5, "day": 20}},                  # 两种输入
            {"latitude": 31.2, "date": {"year": 1990, "month": 5, "day": 20}},  # 半个坐标
            {"latitude": 95, "longitude": 121,
             "date": {"year": 1990, "month": 5, "day": 20}},                  # 纬度越界
            {"place_id": "curated:cn-shanghai",
             "date": {"year": 1990, "month": 5, "day": 20},
             "utc_offset_minutes": 900},                                      # 超引擎口径
            {"place_id": 123, "date": {"year": 1990, "month": 5, "day": 20}},  # 类型错误
        ]
        for body in bad_bodies:
            status, payload = self.post(body)
            self.assertEqual(status, 400, msg=body)
            self.assertEqual(payload["error"]["code"], "INVALID_REQUEST", msg=body)

    def test_resolve_lmt_era_marks_uncertain(self):
        status, payload = self.post({
            "place_id": "curated:cn-shanghai", "date": {"year": 1890, "month": 6, "day": 1},
        })
        self.assertEqual(status, 200)
        data = payload["data"]
        self.assertEqual(data["time"]["confidence"], "uncertain")
        self.assertIn("lmt_uncertain", [w["code"] for w in data["warnings"]])

    # ---- meta ---------------------------------------------------------------
    def test_geo_meta_reports_revision_count_and_tzdata(self):
        status, payload = self.get("/api/v1/geo/meta")
        self.assertEqual(status, 200)
        data = payload["data"]
        self.assertEqual(data["count"], 300)
        self.assertEqual(data["revision"], geo_places.default_index().revision)
        self.assertTrue(data["tz_available"])
        self.assertTrue(str(data["tzdata_version"]))

    @unittest.skipUnless(server.ASTRO_CLI_PATH.exists(), "astro_web_cli has not been built")
    def test_astro_meta_extends_with_geo_block(self):
        status, payload = self.get("/api/v1/astro/meta")
        self.assertEqual(status, 200)
        geo_block = payload["data"]["geo"]
        self.assertEqual(geo_block["count"], 300)
        self.assertTrue(geo_block["tz_available"])

    # ---- 降级：缺 data/geo/ 时 GEO_CONFIG_ERROR（不拖垮其它端点） -------------
    def test_missing_dataset_returns_geo_config_error(self):
        original_root = geo_places.GEO_DATA_ROOT
        original_index = geo_places._DEFAULT_INDEX
        try:
            geo_places.GEO_DATA_ROOT = pathlib.Path(ROOT) / "data" / "geo-does-not-exist"
            geo_places._DEFAULT_INDEX = None
            status, payload = self.get("/api/v1/geo/places?q=%E4%B8%8A%E6%B5%B7")
            self.assertEqual(status, 500)
            self.assertEqual(payload["error"]["code"], "GEO_CONFIG_ERROR")

            status, payload = self.post({
                "place_id": "curated:cn-shanghai",
                "date": {"year": 1990, "month": 5, "day": 20},
            })
            self.assertEqual(status, 500)
            self.assertEqual(payload["error"]["code"], "GEO_CONFIG_ERROR")

            # meta 报告 config 错误但不抛异常（前端据此退回手动模式）
            status, payload = self.get("/api/v1/geo/meta")
            self.assertEqual(status, 200)
            self.assertEqual(payload["data"].get("config_error"), "GEO_CONFIG_ERROR")

            # 健康检查不受影响：降级不失效
            status, payload = self.get("/api/v1/health")
            self.assertEqual(status, 200)
        finally:
            geo_places.GEO_DATA_ROOT = original_root
            geo_places._DEFAULT_INDEX = original_index


if __name__ == "__main__":
    unittest.main()
