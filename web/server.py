#!/usr/bin/env python3
import argparse
import json
import mimetypes
import subprocess
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
CLI_PATH = PROJECT_ROOT / "build" / "examples" / "zi_wei_web_cli"
QIMEN_CLI_PATH = PROJECT_ROOT / "build" / "examples" / "qi_men_web_cli"
API_VERSION = "v1"
ALGORITHM_VERSION = "zhouyilab-core/1.4.1"
MAX_BODY_BYTES = 256 * 1024
_AI_REVIEW_SERVICE = None
_AI_REVIEW_LOCK = None

POST_OPERATIONS = {
    "/api/v1/ziwei/time-correction": "time_correction",
    "/api/v1/ziwei/charts": "chart",
    "/api/v1/ziwei/fortune": "fortune",
    "/api/v1/ziwei/analysis": "analysis",
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
        parsed = urlparse(self.path)
        ai_prefix = "/api/v1/ziwei/research/ai-review"
        if parsed.path == "/api/v1/health":
            self.send_api_success({
                "status": "ok",
                "service": "zhouyilab-ziwei-api",
                "cli_available": CLI_PATH.exists(),
                "qimen_cli_available": QIMEN_CLI_PATH.exists(),
            })
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Request-Id")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        ai_prefix = "/api/v1/ziwei/research/ai-review"
        if parsed.path == "/api/v1/qimen/charts":
            try:
                payload = self.read_json_body()
                self.send_api_success(self.run_engine(QIMEN_CLI_PATH, payload))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
            except subprocess.TimeoutExpired:
                self.send_api_error(504, "CALCULATION_TIMEOUT", "奇门排盘计算超时")
            except CliError as error:
                status = 422 if error.code in {"INVALID_JSON", "INVALID_ARGUMENT", "CALCULATION_FAILED"} else 500
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
        except (AnalysisConfigError, BrightnessConfigError):
            self.send_api_error(500, "ANALYSIS_CONFIG_ERROR", "分析配置加载或校验失败")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            if is_legacy:
                self.send_json(400, {"error": f"输入参数无效：{error}"})
            else:
                self.send_api_error(400, "INVALID_REQUEST", f"输入参数无效：{error}")
        except subprocess.TimeoutExpired:
            self.send_api_error(504, "CALCULATION_TIMEOUT", "排盘计算超时")
        except CliError as error:
            status = 422 if error.code in {"INVALID_JSON", "INVALID_ARGUMENT"} else 500
            self.send_api_error(status, error.code, error.message)
        except Exception:
            self.send_api_error(500, "INTERNAL_ERROR", "服务内部错误")

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
        completed = subprocess.run(
            [str(executable)],
            input=json.dumps(request, ensure_ascii=False),
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
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

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format_string, *args):
        print(f"[web] request_id={self.request_id} {format_string % args}")


class CliError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def main():
    parser = argparse.ArgumentParser(description="ZhouYiLab 紫微斗数 API 与本地页面服务")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    missing_engines = [path for path in (CLI_PATH, QIMEN_CLI_PATH) if not path.exists()]
    if missing_engines:
        missing = "、".join(str(path) for path in missing_engines)
        raise SystemExit(f"缺少 {missing}，请先构建网页 CLI")
    mimetypes.add_type("text/javascript", ".js")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ZhouYiHandler)
    print(f"ZhouYiLab API 与页面已启动：http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
