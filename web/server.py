#!/usr/bin/env python3
import argparse
import json
import mimetypes
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tool_registry import ToolRegistryError, load_tool_registry
from governance import API_KEY_HEADER, Governance

from ziwei_analysis import (
    AnalysisConfigError,
    AnalysisRequestError,
    analyze_natal_chart,
)
from ziwei_brightness import (
    BrightnessConfigError,
    apply_star_brightness,
    normalize_brightness_response,
)
from ziwei_blind_review import generate_blind_packet, load_blind_review_resources
from ziwei_ai_review import (
    AiReviewError,
    AiReviewProviderError,
    AiReviewService,
)
from ziwei_research_engine import ResearchConfigError
from astro_analysis import (
    AstroAnalysisConfigError,
    AstroAnalysisRequestError,
    analyze_natal_chart as analyze_astro_natal_chart,
)
from astro_transit_analysis import (
    DIMENSIONS as ASTRO_DIMENSIONS,
    AstroTransitAnalysisConfigError,
    AstroTransitAnalysisRequestError,
    analyze_transit,
)
from astro_daily_reading import (
    AstroDailyReadingConfigError,
    AstroDailyReadingRequestError,
    analyze_and_render as analyze_and_render_daily_reading,
    render_daily_reading,
)
from astro_natal_analysis import (
    AstroNatalAnalysisConfigError,
    AstroNatalAnalysisRequestError,
    analyze_natal_layout,
)
from ziwei_distribution import (
    compute_ziwei_distribution,
    load_reading_config as load_ziwei_distribution_reading_config,
)
from astro_distribution import (
    AstroDistributionConfigError,
    AstroDistributionRequestError,
    compute_distribution,
    load_reading_config as load_distribution_reading_config,
)
from astro_natal_reading import (
    AstroNatalReadingConfigError,
    AstroNatalReadingRequestError,
    analyze_and_render_natal,
    render_natal_reading,
)
from geo_places import (
    DEFAULT_LIMIT as GEO_DEFAULT_LIMIT,
    MAX_LIMIT as GEO_MAX_LIMIT,
    GeoConfigError,
    GeoInvalidRequest,
    GeoNotFoundError,
    default_index,
    geo_meta,
    resolve_place,
    search_places,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"

# P0-1 工具注册表：清单目录存在则严格加载（坏清单 fail fast），缺失则用内建默认。
try:
    TOOL_REGISTRY = load_tool_registry(PROJECT_ROOT)
except ToolRegistryError as error:
    raise SystemExit(f"工具注册表加载失败：{error}")

_ENGINE_PATHS = TOOL_REGISTRY.engine_paths(PROJECT_ROOT)


def _engine_path(tool_id, default_cli):
    """注册表缺失某工具时回退到内建默认路径，保证任何清单子集都能启动。"""
    return _ENGINE_PATHS.get(tool_id, PROJECT_ROOT / default_cli)


CLI_PATH = _engine_path("ziwei", "build/examples/zi_wei_web_cli")
QIMEN_CLI_PATH = _engine_path("qimen", "build/examples/qi_men_web_cli")
BAZI_CLI_PATH = _engine_path("bazi", "build/examples/ba_zi_web_cli")
LIU_YAO_CLI_PATH = _engine_path("liu_yao", "build/examples/liu_yao_web_cli")
DA_LIU_REN_CLI_PATH = _engine_path("da_liu_ren", "build/examples/da_liu_ren_web_cli")
CALENDAR_CLI_PATH = _engine_path("calendar", "build/examples/common_calendar_web_cli")
ASTRO_CLI_PATH = _engine_path("astro", "build/examples/astro_web_cli")

# P0-2 公网最小治理：默认 observe（只记录不拦截），off/observe/enforce 由环境变量控制。
GOVERNANCE = Governance.from_env(PROJECT_ROOT)

# engine_chart handler 的默认可转 422 的错误码；astro 等引擎在清单 options 里声明自己的集合。
DEFAULT_ENGINE_BAD_REQUEST_CODES = frozenset({
    "INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED",
})

BAZI_SHEN_SHA_ROOT = PROJECT_ROOT / "config" / "bazi" / "shen_sha"
BAZI_SHEN_SHA_ALIASES = {
    "zi_wu_mao_you_si_gong_hu_huan_shen_sha": "子午卯酉四宫互换神煞.json",
    "yin_shen_si_hai_si_gong_hu_huan_shen_sha": "寅申巳亥四宫互换神煞.json",
    "chen_xu_chou_wei_si_gong_hu_huan_shen_sha": "辰戌丑未四宫互换神煞.json",
}
API_VERSION = "v1"
ALGORITHM_VERSION = "zhouyilab-core/1.4.1"
MAX_BODY_BYTES = 256 * 1024
_AI_REVIEW_SERVICE = None
_AI_REVIEW_LOCK = None
_ZIWEI_SYMBOLS_CACHE = None
_DISTRIBUTION_READING_CACHE = None
_ZIWEI_DISTRIBUTION_READING_CACHE = None


def get_ziwei_distribution_reading_config():
    global _ZIWEI_DISTRIBUTION_READING_CACHE
    if _ZIWEI_DISTRIBUTION_READING_CACHE is None:
        _ZIWEI_DISTRIBUTION_READING_CACHE = load_ziwei_distribution_reading_config()
    return _ZIWEI_DISTRIBUTION_READING_CACHE


def get_distribution_reading_config():
    global _DISTRIBUTION_READING_CACHE
    if _DISTRIBUTION_READING_CACHE is None:
        _DISTRIBUTION_READING_CACHE = load_distribution_reading_config()
    return _DISTRIBUTION_READING_CACHE

POST_OPERATIONS = {
    "/api/v1/ziwei/time-correction": "time_correction",
    "/api/v1/calendar/convert": "calendar_convert",
    "/api/v1/calendar/true-solar-time": "calendar_true_solar_time",
    "/api/v1/ziwei/charts": "chart",
    "/api/v1/ziwei/fortune": "fortune",
    "/api/v1/ziwei/analysis": "analysis",
    "/api/v1/astro/analysis": "astro_analysis",
}


def platform_discovery():
    """C3 平台发现端点：工具→路由→页面→文档的自助索引（纯注册表派生）。"""
    summary = TOOL_REGISTRY.summary(PROJECT_ROOT)
    return {
        "service": "zhouyilab-platform",
        "api_version": API_VERSION,
        "algorithm_version": ALGORITHM_VERSION,
        "governance_mode": GOVERNANCE.mode,
        "endpoints": {
            "health": "/api/v1/health",
            "tools": "/api/v1/tools",
            "ziwei_symbols": "/api/v1/ziwei/symbols",
        },
        "tools": [
            {
                "id": tool["id"],
                "name": tool["name"],
                "calibration_status": tool["calibration_status"],
                "visibility": tool.get("visibility", "public"),
                "rule_profile_version": tool.get("rule_profile_version"),
                "interface_doc": tool.get("interface_doc"),
                "pages": tool["pages"],
                "routes": tool["routes"],
            }
            for tool in summary["tools"]
        ],
    }


def get_ai_review_service():
    global _AI_REVIEW_SERVICE, _AI_REVIEW_LOCK
    if _AI_REVIEW_LOCK is None:
        import threading
        _AI_REVIEW_LOCK = threading.Lock()
    with _AI_REVIEW_LOCK:
        if _AI_REVIEW_SERVICE is None:
            _AI_REVIEW_SERVICE = AiReviewService()
    return _AI_REVIEW_SERVICE


def legacy_request(payload):
    birth = payload["birth"]
    target = payload["target"]
    options = payload["options"]
    return {
        "operation": "fortune",
        "birth": {
            **birth,
            "second": birth.get("second", 0),
            "gender": payload["gender"],
        },
        "time_correction": {
            "mode": "true_solar_time" if options["trueSolarTime"] else "standard_time",
            "longitude": options["longitude"],
            "standard_meridian": options.get("standardMeridian", 120),
            "daylight_saving_minutes": options.get("daylightSavingMinutes", 0),
        },
        "target": {
            **target,
            "second": target.get("second", 0),
            "age": payload["age"],
        },
    }


def legacy_response(result):
    return {
        **result["chart"],
        "target": result["target"],
        "fortune": result["fortune"],
    }


class ZhouYiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.request_id = uuid.uuid4().hex
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def do_GET(self):
        self._request_started = time.monotonic()
        parsed = urlparse(self.path)
        if not self._governance_gate(parsed):
            return
        ai_prefix = "/api/v1/ziwei/research/ai-review"
        if parsed.path == "/api/v1/health":
            self.send_api_success(self._health_payload())
            return
        if parsed.path in ("/api/v1", "/api/v1/"):
            self.send_api_success(platform_discovery())
            return
        if parsed.path == "/api/v1/tools":
            self.send_api_success(TOOL_REGISTRY.summary(PROJECT_ROOT))
            return
        # GET 注册表分发放在平台内建端点之后：/api/v1/health、/api/v1/tools 不可被清单覆盖。
        get_binding = TOOL_REGISTRY.resolve("GET", parsed.path)
        if get_binding is not None and get_binding[1].handler == "static_config":
            self._handle_static_config(get_binding)
            return
        if parsed.path == "/api/v1/astro/meta":
            if not ASTRO_CLI_PATH.exists():
                self.send_api_error(500, "ENGINE_UNAVAILABLE", "Astro 计算引擎尚未构建")
                return
            try:
                result = self.run_engine(ASTRO_CLI_PATH, {"operation": "meta"})
                # 天文页签自洽：附带同一份中立地名/时区元数据（方案 §7）
                result["geo"] = geo_meta()
                self.send_api_success(result)
            except CliError as error:
                self.send_api_error(500, error.code, error.message)
            return
        if parsed.path == "/api/v1/geo/meta":
            self.send_api_success(geo_meta())
            return
        if parsed.path == "/api/v1/geo/places":
            try:
                params = parse_qs(parsed.query, keep_blank_values=True)
                raw_query = params.get("q", [None])[0]
                if raw_query is None or not raw_query.strip():
                    raise GeoInvalidRequest("缺少查询参数 q")
                raw_limit = params.get("limit", [GEO_DEFAULT_LIMIT])[0]
                try:
                    limit = int(raw_limit)
                except (TypeError, ValueError):
                    raise GeoInvalidRequest("limit 必须是整数")
                if not 1 <= limit <= GEO_MAX_LIMIT:
                    raise GeoInvalidRequest(f"limit 必须在 1 到 {GEO_MAX_LIMIT} 之间")
                country = (params.get("country", [None])[0] or "").strip() or None
                if country and (len(country) != 2 or not country.isalpha()):
                    raise GeoInvalidRequest("country 必须是两位国家/地区码")
                index = default_index()
                hits = search_places(index, raw_query, limit=limit, country=country)
                self.send_api_success({
                    "query": raw_query.strip(),
                    "count": len(hits),
                    "revision": index.revision,
                    "results": hits,
                })
            except GeoNotFoundError as error:
                self.send_api_error(404, error.code, error.user_message())
            except GeoConfigError as error:
                self.send_api_error(500, error.code, error.user_message())
            except GeoInvalidRequest as error:
                self.send_api_error(400, "INVALID_REQUEST", error.user_message())
            return
        if parsed.path == "/api/v1/ziwei/symbols":
            # P0-4 内核权威符号字典：同一二进制版本内不变，进程级缓存一次即可。
            try:
                self.send_api_success(self._ziwei_symbols())
            except CliError as error:
                self.send_api_error(500, error.code, error.message)
            return
        if parsed.path == "/api/v1/ziwei/meta":
            self.send_api_success({
                "api_version": API_VERSION,
                "algorithm_version": ALGORITHM_VERSION,
                "capabilities": [
                    "natal_chart", "true_solar_time", "decade", "minor",
                    "annual", "monthly", "daily", "hourly", "fortune_transit_stars",
                    "natal_shen_sha",
                    "natal_analysis_fragments",
                    "natal_structured_sections",
                    "natal_ai_packet",
                    "natal_shen_sha_analysis",
                    "declarative_pattern_engine",
                    "pattern_condition_trace",
                    "focus_palace_pattern_attribution",
                    "local_blind_review_packet",
                    "ai_multi_model_review_lab",
                ],
                "genders": ["male", "female"],
                "time_correction_modes": ["standard_time", "true_solar_time"],
                "fortune_layers": [
                    "decade", "minor", "annual", "monthly", "daily", "hourly"
                ],
                "analysis_layers": ["natal"],
                "analysis_input_modes": ["chart_request", "chart"],
            })
            return
        if parsed.path == f"{ai_prefix}/meta":
            try:
                service = get_ai_review_service()
                provider_meta = service.provider_meta()
                self.send_api_success({
                    "protocol": service.protocol,
                    "provider_config_path": provider_meta["config_path"],
                    "providers": provider_meta["providers"],
                    "storage": {
                        "database": str(service.store.path),
                        "api_keys_persisted": False,
                    },
                })
            except ResearchConfigError as error:
                self.send_api_error(500, "RESEARCH_CONFIG_ERROR", str(error))
            return
        if parsed.path == f"{ai_prefix}/experiments":
            try:
                self.send_api_success(get_ai_review_service().store.list_experiments())
            except ResearchConfigError as error:
                self.send_api_error(500, "RESEARCH_CONFIG_ERROR", str(error))
            return
        if parsed.path.startswith(f"{ai_prefix}/experiments/"):
            parts = parsed.path[len(f"{ai_prefix}/experiments/"):].split("/")
            experiment_id = parts[0]
            try:
                service = get_ai_review_service()
                if len(parts) == 1:
                    data = service.store.get_experiment(experiment_id)
                elif len(parts) == 2 and parts[1] == "results":
                    data = service.results(experiment_id)
                else:
                    self.send_api_error(404, "ENDPOINT_NOT_FOUND", "接口不存在")
                    return
                self.send_api_success(data)
            except AiReviewError as error:
                self.send_api_error(404, "AI_REVIEW_NOT_FOUND", str(error))
            except ResearchConfigError as error:
                self.send_api_error(500, "RESEARCH_CONFIG_ERROR", str(error))
            return
        if parsed.path == "/api/v1/ziwei/research/blind-review/packet":
            try:
                seed = parse_qs(
                    parsed.query, keep_blank_values=True
                ).get("seed", ["pilot-2026"])[0]
                if not seed or len(seed) > 128:
                    raise ValueError("seed 长度必须为 1-128 个字符")
            except (TypeError, ValueError) as error:
                self.send_api_error(400, "INVALID_REQUEST", str(error))
                return
            try:
                resources, protocol = load_blind_review_resources()
                packet, _ = generate_blind_packet(resources, protocol, seed)
                self.send_api_success(packet)
            except (ResearchConfigError, KeyError, TypeError, ValueError) as error:
                self.send_api_error(500, "RESEARCH_CONFIG_ERROR", str(error))
            return
        if parsed.path.startswith("/api/v1/bazi/shen-sha/"):
            shen_sha_id = parsed.path.rsplit("/", 1)[-1]
            if not shen_sha_id or not all(
                character.isascii() and (character.isalnum() or character == "_")
                for character in shen_sha_id
            ):
                self.send_api_error(400, "INVALID_SHEN_SHA_ID", "神煞 ID 无效")
                return
            resource_path = BAZI_SHEN_SHA_ROOT / BAZI_SHEN_SHA_ALIASES.get(shen_sha_id, f"{shen_sha_id}.json")
            if not resource_path.is_file():
                self.send_api_error(404, "SHEN_SHA_NOT_FOUND", "神煞说明尚未收录")
                return
            try:
                resource = json.loads(resource_path.read_text(encoding="utf-8"))
                source_document = resource.get("source_document")
                if source_document:
                    document_path = PROJECT_ROOT / source_document
                    if document_path.is_file():
                        resource["document_markdown"] = document_path.read_text(encoding="utf-8")
                self.send_api_success(resource)
            except (OSError, json.JSONDecodeError):
                self.send_api_error(500, "SHEN_SHA_RESOURCE_ERROR", "神煞说明加载失败")
            return
        if parsed.path.startswith("/api/"):
            self.send_api_error(404, "ENDPOINT_NOT_FOUND", "接口不存在")
            return
        super().do_GET()

    def do_OPTIONS(self):
        if not self.path.startswith("/api/"):
            self.send_error(404)
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Request-Id, X-API-Key")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_POST(self):
        self._request_started = time.monotonic()
        parsed = urlparse(self.path)
        if not self._governance_gate(parsed):
            return
        ai_prefix = "/api/v1/ziwei/research/ai-review"
        binding = TOOL_REGISTRY.resolve("POST", parsed.path)
        if binding is not None and binding[1].handler == "engine_chart":
            self._handle_engine_chart(binding)
            return
        if parsed.path == "/api/v1/geo/place-resolve":
            # 只读解析：不产生副作用，不改排盘契约（方案 §7）
            try:
                payload = self.read_json_body()
                place_id = payload.get("place_id")
                query = payload.get("query")
                latitude = payload.get("latitude")
                longitude = payload.get("longitude")
                supplied = sum(
                    value is not None
                    for value in (
                        place_id if isinstance(place_id, str) and place_id.strip() else None,
                        query if isinstance(query, str) and query.strip() else None,
                        None if (latitude is None or longitude is None) else "coord",
                    )
                )
                if supplied != 1:
                    raise GeoInvalidRequest("place_id、query、latitude/longitude 必须且只能提供一种")
                if place_id is not None and not isinstance(place_id, str):
                    raise GeoInvalidRequest("place_id 必须是字符串")
                if query is not None and not isinstance(query, str):
                    raise GeoInvalidRequest("query 必须是字符串")
                for name, value in (("latitude", latitude), ("longitude", longitude)):
                    if value is not None and not isinstance(value, (int, float)):
                        raise GeoInvalidRequest(f"{name} 必须是数字")
                offset = payload.get("utc_offset_minutes")
                if offset is not None and not isinstance(offset, int):
                    raise GeoInvalidRequest("utc_offset_minutes 必须是整数")
                house_system = payload.get("house_system")
                if house_system is not None and not isinstance(house_system, str):
                    raise GeoInvalidRequest("house_system 必须是字符串")
                result = resolve_place(
                    default_index(),
                    place_id=place_id,
                    query=query,
                    lat=latitude,
                    lon=longitude,
                    birth_date=payload.get("date"),
                    utc_offset_minutes=offset,
                    house_system=house_system,
                )
                self.send_api_success(result)
            except GeoNotFoundError as error:
                self.send_api_error(404, error.code, error.user_message())
            except GeoConfigError as error:
                self.send_api_error(500, error.code, error.user_message())
            except GeoInvalidRequest as error:
                self.send_api_error(400, "INVALID_REQUEST", error.user_message())
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
            return
        if parsed.path == "/api/v1/astro/charts":
            try:
                payload = self.read_json_body()
                self.send_api_success(self.run_engine(ASTRO_CLI_PATH, payload))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
            except subprocess.TimeoutExpired:
                self.send_api_error(504, "CALCULATION_TIMEOUT", "西洋占星计算超时")
            except CliError as error:
                status = 422 if error.code in {"INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED", "EPHEMERIS_UNAVAILABLE", "HOUSE_CALCULATION_FAILED", "INVALID_REQUEST"} else 500
                self.send_api_error(status, error.code, error.message)
            return
        if parsed.path == "/api/v1/astro/transits":
            try:
                payload = self.read_json_body()
                self.send_api_success(self.run_engine(ASTRO_CLI_PATH, {**payload, "operation": "transit"}))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
            except subprocess.TimeoutExpired:
                self.send_api_error(504, "CALCULATION_TIMEOUT", "西洋占星行运计算超时")
            except CliError as error:
                status = 422 if error.code in {"INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED", "EPHEMERIS_UNAVAILABLE", "HOUSE_CALCULATION_FAILED", "INVALID_REQUEST"} else 500
                self.send_api_error(status, error.code, error.message)
            return
        if parsed.path == "/api/v1/astro/transit-analysis":
            try:
                payload = self.read_json_body()
                result = self.run_astro_transit_analysis(payload)
                self.send_api_success(result)
            except (AstroTransitAnalysisConfigError,):
                self.send_api_error(500, "ANALYSIS_CONFIG_ERROR", "行运分析规则配置加载或校验失败")
            except AstroTransitAnalysisRequestError as error:
                self.send_api_error(400, "INVALID_REQUEST", str(error))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
            except subprocess.TimeoutExpired:
                self.send_api_error(504, "CALCULATION_TIMEOUT", "西洋占星行运分析计算超时")
            except CliError as error:
                status = 422 if error.code in {
                    "INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED",
                    "EPHEMERIS_UNAVAILABLE", "HOUSE_CALCULATION_FAILED", "INVALID_REQUEST",
                } else 500
                self.send_api_error(status, error.code, error.message)
            return
        if parsed.path == "/api/v1/astro/daily-reading":
            try:
                payload = self.read_json_body()
                self.send_api_success(self.run_astro_daily_reading(payload))
            except AstroDailyReadingConfigError as error:
                self.send_api_error(500, "ANALYSIS_CONFIG_ERROR", str(error))
            except AstroDailyReadingRequestError as error:
                self.send_api_error(400, "INVALID_REQUEST", str(error))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
            except subprocess.TimeoutExpired:
                self.send_api_error(504, "CALCULATION_TIMEOUT", "西洋占星日运计算超时")
            except CliError as error:
                status = 422 if error.code in {
                    "INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED",
                    "EPHEMERIS_UNAVAILABLE", "HOUSE_CALCULATION_FAILED", "INVALID_REQUEST",
                } else 500
                self.send_api_error(status, error.code, error.message)
            return
        if parsed.path == "/api/v1/ziwei/distribution":
            try:
                payload = self.read_json_body()
                self.send_api_success(self.run_ziwei_distribution(payload))
            except (AstroDistributionConfigError, AstroDistributionRequestError) as error:
                status = 500 if isinstance(error, AstroDistributionConfigError) else 400
                code = "ANALYSIS_CONFIG_ERROR" if status == 500 else "INVALID_REQUEST"
                self.send_api_error(status, code, str(error))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
            except subprocess.TimeoutExpired:
                self.send_api_error(504, "CALCULATION_TIMEOUT", "紫微分布画像计算超时")
            except CliError as error:
                status = 422 if error.code in {
                    "INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED",
                } else 500
                self.send_api_error(status, error.code, error.message)
            return
        if parsed.path == "/api/v1/astro/distribution":
            try:
                payload = self.read_json_body()
                self.send_api_success(self.run_astro_distribution(payload))
            except AstroDistributionConfigError as error:
                self.send_api_error(500, "ANALYSIS_CONFIG_ERROR", str(error))
            except AstroDistributionRequestError as error:
                self.send_api_error(400, "INVALID_REQUEST", str(error))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
            except subprocess.TimeoutExpired:
                self.send_api_error(504, "CALCULATION_TIMEOUT", "西洋占星分布画像计算超时")
            except CliError as error:
                status = 422 if error.code in {
                    "INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED",
                    "EPHEMERIS_UNAVAILABLE", "HOUSE_CALCULATION_FAILED", "INVALID_REQUEST",
                } else 500
                self.send_api_error(status, error.code, error.message)
            return
        if parsed.path == "/api/v1/astro/natal-analysis":
            try:
                payload = self.read_json_body()
                self.send_api_success(self.run_astro_natal_analysis(payload))
            except AstroNatalAnalysisConfigError as error:
                self.send_api_error(500, "ANALYSIS_CONFIG_ERROR", str(error))
            except AstroNatalAnalysisRequestError as error:
                self.send_api_error(400, "INVALID_REQUEST", str(error))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
            except subprocess.TimeoutExpired:
                self.send_api_error(504, "CALCULATION_TIMEOUT", "西洋占星本命布局分析计算超时")
            except CliError as error:
                status = 422 if error.code in {
                    "INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED",
                    "EPHEMERIS_UNAVAILABLE", "HOUSE_CALCULATION_FAILED", "INVALID_REQUEST",
                } else 500
                self.send_api_error(status, error.code, error.message)
            return
        if parsed.path == "/api/v1/astro/natal-reading":
            try:
                payload = self.read_json_body()
                self.send_api_success(self.run_astro_natal_reading(payload))
            except (AstroNatalAnalysisConfigError, AstroNatalReadingConfigError) as error:
                self.send_api_error(500, "ANALYSIS_CONFIG_ERROR", str(error))
            except (AstroNatalAnalysisRequestError, AstroNatalReadingRequestError) as error:
                self.send_api_error(400, "INVALID_REQUEST", str(error))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
            except subprocess.TimeoutExpired:
                self.send_api_error(504, "CALCULATION_TIMEOUT", "西洋占星本命布局解读计算超时")
            except CliError as error:
                status = 422 if error.code in {
                    "INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED",
                    "EPHEMERIS_UNAVAILABLE", "HOUSE_CALCULATION_FAILED", "INVALID_REQUEST",
                } else 500
                self.send_api_error(status, error.code, error.message)
            return
        if parsed.path == f"{ai_prefix}/connections/test":
            try:
                payload = self.read_json_body()
                service = get_ai_review_service()
                provider_id = payload.get("provider_id")
                if not isinstance(provider_id, str):
                    raise AiReviewError("必须提供 provider_id")
                self.send_api_success(service.test_connection(provider_id))
            except AiReviewProviderError as error:
                self.send_api_error(502, "AI_PROVIDER_UNAVAILABLE", str(error))
            except (AiReviewError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_AI_PROVIDER", str(error))
            except ResearchConfigError as error:
                self.send_api_error(500, "RESEARCH_CONFIG_ERROR", str(error))
            return
        if parsed.path == f"{ai_prefix}/experiments":
            try:
                payload = self.read_json_body()
                self.send_api_success(get_ai_review_service().create_experiment(payload), 202)
            except (AiReviewError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_AI_EXPERIMENT", str(error))
            except ResearchConfigError as error:
                self.send_api_error(500, "RESEARCH_CONFIG_ERROR", str(error))
            return
        cancel_prefix = f"{ai_prefix}/experiments/"
        if parsed.path.startswith(cancel_prefix) and parsed.path.endswith("/cancel"):
            experiment_id = parsed.path[len(cancel_prefix):-len("/cancel")]
            try:
                self.read_json_body()
                service = get_ai_review_service()
                service.store.request_cancel(experiment_id)
                self.send_api_success(service.store.get_experiment(experiment_id), 202)
            except (AiReviewError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_AI_EXPERIMENT", str(error))
            return

        is_legacy = parsed.path == "/api/calculate"
        operation = POST_OPERATIONS.get(parsed.path)
        if operation is None and not is_legacy:
            self.send_api_error(404, "ENDPOINT_NOT_FOUND", "接口不存在")
            return

        try:
            payload = self.read_json_body()
            if operation == "analysis":
                result = self.run_analysis(payload)
            elif operation == "astro_analysis":
                result = self.run_astro_analysis(payload)
            elif operation in {"calendar_convert", "calendar_true_solar_time"}:
                result = self.run_engine(CALENDAR_CLI_PATH, {
                    **payload,
                    "operation": "convert"
                        if operation == "calendar_convert"
                        else "true_solar_time",
                })
            else:
                request = legacy_request(payload) if is_legacy else {
                    **payload,
                    "operation": operation,
                }
                result = self.run_cli(request)
            if is_legacy:
                self.send_json(200, legacy_response(result))
            else:
                self.send_api_success(result)
        except (AnalysisConfigError, BrightnessConfigError, AstroAnalysisConfigError):
            self.send_api_error(500, "ANALYSIS_CONFIG_ERROR", "分析配置加载或校验失败")
        except AstroAnalysisRequestError as error:
            self.send_api_error(400, "INVALID_REQUEST", str(error))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            if is_legacy:
                self.send_json(400, {"error": f"输入参数无效：{error}"})
            else:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
        except subprocess.TimeoutExpired:
            self.send_api_error(504, "CALCULATION_TIMEOUT", "排盘计算超时")
        except CliError as error:
            status = 422 if error.code in {
                "INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED",
                "EPHEMERIS_UNAVAILABLE", "HOUSE_CALCULATION_FAILED", "INVALID_REQUEST",
            } else 500
            self.send_api_error(status, error.code, error.message)
        except Exception:
            self.send_api_error(500, "INTERNAL_ERROR", "服务内部错误")

    def _ziwei_symbols(self):
        global _ZIWEI_SYMBOLS_CACHE
        if _ZIWEI_SYMBOLS_CACHE is None:
            _ZIWEI_SYMBOLS_CACHE = self.run_engine(CLI_PATH, {"operation": "symbols"})
        return _ZIWEI_SYMBOLS_CACHE

    def _health_payload(self):
        # 保留既有字面量字段作为公开契约（向后兼容），并追加注册表派生的
        # 引擎可用性与各术数校准状态。engine 常量在注册表缺失时已回退内建路径。
        payload = {
            "status": "ok",
            "service": "zhouyilab-ziwei-api",
            "cli_available": CLI_PATH.exists(),
            "qimen_cli_available": QIMEN_CLI_PATH.exists(),
            "bazi_cli_available": BAZI_CLI_PATH.exists(),
            "liu_yao_cli_available": LIU_YAO_CLI_PATH.exists(),
            "da_liu_ren_cli_available": DA_LIU_REN_CLI_PATH.exists(),
            "calendar_cli_available": CALENDAR_CLI_PATH.exists(),
            "astro_cli_available": ASTRO_CLI_PATH.exists(),
            "astro_ephemeris_available": any(
                path.is_file()
                for path in (Path(os.environ["ZHOUYILAB_EPHEMERIS_PATH"])
                             if os.environ.get("ZHOUYILAB_EPHEMERIS_PATH")
                             else PROJECT_ROOT / "data" / "ephemeris").rglob("*.se1")
            ),
            "registry_source": TOOL_REGISTRY.source,
            "tools": TOOL_REGISTRY.calibration_map(),
        }
        # 叠加注册表派生键：通过 manifest 新增的工具自动获得可用性字段
        payload.update(TOOL_REGISTRY.health_flags(PROJECT_ROOT))
        return payload

    def _governance_gate(self, parsed):
        """P0-2 治理关卡。返回 False 表示请求已被拦截并响应完毕。"""
        self._gov_decision = GOVERNANCE.decide(
            self.headers.get(API_KEY_HEADER),
            parsed.path,
            self.client_address[0] if self.client_address else "-",
        )
        decision = self._gov_decision
        if decision.get("blocked"):
            self.send_api_error(decision["status"], decision["code"], decision["message"])
            return False
        return True

    def _handle_static_config(self, binding):
        """注册表 static_config handler：只读暴露 config/ 下的声明式 JSON（如术语库）。"""
        manifest, route = binding
        rel = route.options["config_path"]
        path = (PROJECT_ROOT / rel).resolve()
        if PROJECT_ROOT.resolve() not in path.parents or not path.is_file():
            self.send_api_error(404, route.options.get("not_found_code", "CONFIG_NOT_FOUND"),
                                f"{manifest.name}配置尚未收录")
            return
        try:
            self.send_api_success(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            self.send_api_error(500, "CONFIG_ERROR", f"{manifest.name}配置加载失败")

    def _handle_engine_chart(self, binding):
        """注册表 engine_chart handler：清单声明即路由，无需新增 server 分支。"""
        manifest, route = binding
        engine = manifest.engine_path(PROJECT_ROOT)
        timeout_message = route.options.get("timeout_message", f"{manifest.name}计算超时")
        bad_codes = frozenset(route.options.get(
            "bad_request_codes", DEFAULT_ENGINE_BAD_REQUEST_CODES))
        try:
            payload = self.read_json_body()
            operation = route.options.get("operation")
            request = {**payload, "operation": operation} if operation else payload
            self.send_api_success(self.run_engine(engine, request))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
        except subprocess.TimeoutExpired:
            self.send_api_error(504, "CALCULATION_TIMEOUT", timeout_message)
        except CliError as error:
            status = 422 if error.code in bad_codes else 500
            self.send_api_error(status, error.code, error.message)

    def read_json_body(self):
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if content_type != "application/json":
            raise ValueError("Content-Type 必须是 application/json")
        size = int(self.headers.get("Content-Length", "0"))
        if size <= 0 or size > MAX_BODY_BYTES:
            raise ValueError("请求内容大小不正确")
        payload = json.loads(self.rfile.read(size))
        if not isinstance(payload, dict):
            raise TypeError("请求体必须是 JSON 对象")
        return payload

    def run_cli(self, request):
        return self.run_engine(CLI_PATH, request, normalize=True)

    def run_engine(self, executable, request, normalize=False):
        if not executable.exists():
            raise CliError("ENGINE_UNAVAILABLE", "计算引擎尚未构建")
        engine_env = os.environ.copy()
        engine_env.setdefault(
            "ZHOUYILAB_EPHEMERIS_PATH",
            str(PROJECT_ROOT / "data" / "ephemeris"),
        )
        completed = subprocess.run(
            [str(executable)],
            input=json.dumps(request, ensure_ascii=False),
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            env=engine_env,
            timeout=20,
            check=False,
        )
        try:
            result = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as error:
            raise CliError("INVALID_ENGINE_RESPONSE", "计算引擎返回了无效 JSON") from error
        if completed.returncode != 0 or "error" in result:
            error = result.get("error", {})
            if isinstance(error, str):
                raise CliError("CALCULATION_FAILED", error)
            raise CliError(
                error.get("code", "CALCULATION_FAILED"),
                error.get("message", "排盘计算失败"),
            )
        return normalize_brightness_response(result) if normalize else result

    def run_analysis(self, payload):
        chart = payload.get("chart")
        chart_request = payload.get("chart_request")
        if chart is not None and chart_request is not None:
            raise AnalysisRequestError("chart 与 chart_request 只能提供一个")
        if chart is None:
            if not isinstance(chart_request, dict):
                raise AnalysisRequestError("必须提供 chart 或 chart_request")
            chart = self.run_cli({**chart_request, "operation": "chart"})
        if not isinstance(chart, dict):
            raise AnalysisRequestError("chart 必须是 JSON 对象")
        apply_star_brightness(chart)
        return {
            "chart": chart,
            "analysis": analyze_natal_chart(chart, payload.get("scope")),
        }

    def run_astro_analysis(self, payload):
        chart = payload.get("chart")
        chart_request = payload.get("chart_request")
        if chart is not None and chart_request is not None:
            raise AstroAnalysisRequestError("chart 与 chart_request 只能提供一个")
        if chart is None:
            if not isinstance(chart_request, dict):
                raise AstroAnalysisRequestError("必须提供 chart 或 chart_request")
            chart = self.run_engine(ASTRO_CLI_PATH, {**chart_request, "operation": "chart"})
        return {
            "chart": chart,
            "analysis": analyze_astro_natal_chart(chart, payload.get("scope")),
        }

    def run_astro_transit_analysis(self, payload):
        chart = payload.get("chart")
        transit_request = payload.get("transit_request")
        if chart is not None and transit_request is not None:
            raise AstroTransitAnalysisRequestError("chart 与 transit_request 只能提供一个")
        if chart is None:
            if not isinstance(transit_request, dict):
                raise AstroTransitAnalysisRequestError("必须提供 chart 或 transit_request")
            chart = self.run_engine(ASTRO_CLI_PATH, {**transit_request, "operation": "transit"})
        if not isinstance(chart, dict):
            raise AstroTransitAnalysisRequestError("chart 必须是 JSON 对象")
        return analyze_transit(
            chart,
            payload.get("scope"),
            payload.get("dimensions"),
        )

    def run_astro_daily_reading(self, payload):
        chart = payload.get("chart")
        transit_request = payload.get("transit_request")
        analysis = payload.get("analysis")
        supplied = sum(value is not None for value in (chart, transit_request, analysis))
        if supplied > 1:
            raise AstroDailyReadingRequestError(
                "chart、transit_request、analysis 只能提供一个"
            )
        period = payload.get("period", "day")
        scope = payload.get("scope")
        if isinstance(scope, str):
            if period != "day" and period != scope:
                raise AstroDailyReadingRequestError("period 与 scope 的时间范围不一致")
            period = scope
            scope = None
        if period != "day":
            raise AstroDailyReadingRequestError("A3 目前只支持 day 时间范围")
        dimensions = payload.get("dimensions")
        requested_date = payload.get("date")
        if analysis is not None:
            if not isinstance(analysis, dict):
                raise AstroDailyReadingRequestError("analysis 必须是 JSON 对象")
            if scope is not None and dimensions is not None and scope != dimensions:
                raise AstroDailyReadingRequestError("scope 与 dimensions 只能提供一个")
            requested_dimensions = dimensions if dimensions is not None else scope
            if requested_dimensions is not None:
                if (
                    not isinstance(requested_dimensions, list)
                    or not requested_dimensions
                    or any(not isinstance(item, str) for item in requested_dimensions)
                    or not set(requested_dimensions).issubset(ASTRO_DIMENSIONS)
                ):
                    raise AstroDailyReadingRequestError(
                        "scope 或 dimensions 必须是支持的非空生活领域数组"
                    )
                analysis = {
                    **analysis,
                    "signals": [
                        signal for signal in analysis.get("signals", [])
                        if signal.get("dimension") in requested_dimensions
                    ],
                }
            return render_daily_reading(
                analysis,
                requested_date=requested_date,
            )
        if chart is None:
            if not isinstance(transit_request, dict):
                raise AstroDailyReadingRequestError(
                    "必须提供 chart、transit_request 或 analysis"
                )
            chart = self.run_engine(
                ASTRO_CLI_PATH,
                {**transit_request, "operation": "transit"},
            )
        if not isinstance(chart, dict):
            raise AstroDailyReadingRequestError("chart 必须是 JSON 对象")
        return analyze_and_render_daily_reading(
            chart,
            scope=scope,
            dimensions=dimensions,
            requested_date=requested_date,
        )

    def run_ziwei_distribution(self, payload):
        chart = payload.get("chart")
        chart_request = payload.get("chart_request")
        if chart is not None and chart_request is not None:
            raise AstroDistributionRequestError("chart 与 chart_request 只能提供一个")
        if chart is None:
            if not isinstance(chart_request, dict):
                raise AstroDistributionRequestError("必须提供 chart 或 chart_request")
            chart = self.run_cli({**chart_request, "operation": "chart"})
        label = payload.get("label")
        if label is not None and (not isinstance(label, str) or len(label) > 60):
            raise AstroDistributionRequestError("label 必须是不超过 60 字符的字符串")
        return compute_ziwei_distribution(chart, self._ziwei_symbols(),
                                         get_ziwei_distribution_reading_config(), label=label)

    def run_astro_distribution(self, payload):
        chart = payload.get("chart")
        chart_request = payload.get("chart_request")
        if chart is not None and chart_request is not None:
            raise AstroDistributionRequestError("chart 与 chart_request 只能提供一个")
        if chart is None:
            if not isinstance(chart_request, dict):
                raise AstroDistributionRequestError("必须提供 chart 或 chart_request")
            chart = self.run_engine(ASTRO_CLI_PATH, {**chart_request, "operation": "chart"})
        label = payload.get("label")
        if label is not None and (not isinstance(label, str) or len(label) > 60):
            raise AstroDistributionRequestError("label 必须是不超过 60 字符的字符串")
        return compute_distribution(chart, get_distribution_reading_config(), label=label)

    def run_astro_natal_analysis(self, payload):
        chart = payload.get("chart")
        chart_request = payload.get("chart_request")
        if chart is not None and chart_request is not None:
            raise AstroNatalAnalysisRequestError("chart 与 chart_request 只能提供一个")
        if chart is None:
            if not isinstance(chart_request, dict):
                raise AstroNatalAnalysisRequestError("必须提供 chart 或 chart_request")
            chart = self.run_engine(ASTRO_CLI_PATH, {**chart_request, "operation": "chart"})
        if not isinstance(chart, dict):
            raise AstroNatalAnalysisRequestError("chart 必须是 JSON 对象")
        return analyze_natal_layout(chart, payload.get("ruler_system"))

    def run_astro_natal_reading(self, payload):
        chart = payload.get("chart")
        chart_request = payload.get("chart_request")
        analysis = payload.get("analysis")
        supplied = sum(value is not None for value in (chart, chart_request, analysis))
        if supplied > 1:
            raise AstroNatalReadingRequestError("chart、chart_request、analysis 只能提供一个")
        ruler_system = payload.get("ruler_system")
        if analysis is not None:
            if not isinstance(analysis, dict):
                raise AstroNatalReadingRequestError("analysis 必须是 JSON 对象")
            if ruler_system is not None:
                raise AstroNatalReadingRequestError("传入 analysis 时不再接受 ruler_system")
            return render_natal_reading(analysis)
        if chart is None:
            if not isinstance(chart_request, dict):
                raise AstroNatalReadingRequestError("必须提供 chart、chart_request 或 analysis")
            chart = self.run_engine(ASTRO_CLI_PATH, {**chart_request, "operation": "chart"})
        if not isinstance(chart, dict):
            raise AstroNatalReadingRequestError("chart 必须是 JSON 对象")
        return analyze_and_render_natal(chart, ruler_system=ruler_system)

    def send_api_success(self, data, status=200):
        self.send_json(status, {
            "success": True,
            "data": data,
            "meta": self.response_meta(),
        })

    def send_api_error(self, status, code, message, details=None):
        error = {"code": code, "message": message}
        if details:
            error["details"] = details
        self.send_json(status, {
            "success": False,
            "error": error,
            "meta": self.response_meta(),
        })

    def response_meta(self):
        return {
            "api_version": API_VERSION,
            "algorithm_version": ALGORITHM_VERSION,
            "request_id": self.request_id,
        }

    def send_json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Request-Id", self.request_id)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_response(self, code, message=None):
        self._last_status = code
        super().send_response(code, message)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format_string, *args):
        print(f"[web] request_id={self.request_id} {format_string % args}")
        self._record_access(format_string, args)

    def _record_access(self, format_string, args):
        """P0-2 访问日志：只记录 log_request 的标准形态，写盘失败自动降级。"""
        if GOVERNANCE.mode == "off" or GOVERNANCE.log is None:
            return
        if format_string != '"%s" %s %s' or len(args) < 2:
            return
        try:
            status = int(args[1])
        except (TypeError, ValueError):
            status = None
        decision = getattr(self, "_gov_decision", None) or {}
        duration_ms = None
        if getattr(self, "_request_started", None) is not None:
            duration_ms = round((time.monotonic() - self._request_started) * 1000, 2)
        GOVERNANCE.log.write({
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "request_id": self.request_id,
            "method": getattr(self, "command", None),
            "path": getattr(self, "path", None),
            "status": status,
            "duration_ms": duration_ms,
            "client_ip": self.client_address[0] if self.client_address else None,
            "api": bool(getattr(self, "path", "").startswith("/api/")),
            "governance_mode": decision.get("mode"),
            "governance_decision": decision.get("decision"),
            "governance_key_label": decision.get("key_label"),
            "governance_would_block": decision.get("would_block"),
            "governance_blocked": decision.get("blocked"),
        })


class CliError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def main():
    parser = argparse.ArgumentParser(description="ZhouYiLab 紫微斗数 API 与本地页面服务")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    # 启动门槛由注册表推导：required_at_startup=false 或 optional_env 关闭的引擎豁免。
    required_engines = TOOL_REGISTRY.required_startup_engine_paths(PROJECT_ROOT, os.environ)
    missing_engines = [path for path in required_engines if not path.exists()]
    if missing_engines:
        missing = "、".join(str(path) for path in missing_engines)
        raise SystemExit(f"缺少 {missing}，请先构建网页 CLI")
    mimetypes.add_type("text/javascript", ".js")
    bind_host = os.environ.get("ZHOUYILAB_BIND_HOST", "127.0.0.1")
    server = ThreadingHTTPServer((bind_host, args.port), ZhouYiHandler)
    display_host = "127.0.0.1" if bind_host == "0.0.0.0" else bind_host
    print(f"ZhouYiLab API 与页面已启动：http://{display_host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
