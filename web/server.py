#!/usr/bin/env python3
import argparse
import json
import mimetypes
import subprocess
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

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


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
CLI_PATH = PROJECT_ROOT / "build" / "examples" / "zi_wei_web_cli"
API_VERSION = "v1"
ALGORITHM_VERSION = "zhouyilab-core/1.4.0"
MAX_BODY_BYTES = 64 * 1024

POST_OPERATIONS = {
    "/api/v1/ziwei/time-correction": "time_correction",
    "/api/v1/ziwei/charts": "chart",
    "/api/v1/ziwei/fortune": "fortune",
    "/api/v1/ziwei/analysis": "analysis",
}


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
        if self.path == "/api/v1/health":
            self.send_api_success({
                "status": "ok",
                "service": "zhouyilab-ziwei-api",
                "cli_available": CLI_PATH.exists(),
            })
            return
        if self.path == "/api/v1/ziwei/meta":
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
        if self.path.startswith("/api/"):
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
        is_legacy = self.path == "/api/calculate"
        operation = POST_OPERATIONS.get(self.path)
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
        completed = subprocess.run(
            [str(CLI_PATH)],
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
        return normalize_brightness_response(result)

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
    if not CLI_PATH.exists():
        raise SystemExit(f"缺少 {CLI_PATH}，请先构建 zi_wei_web_cli")
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
