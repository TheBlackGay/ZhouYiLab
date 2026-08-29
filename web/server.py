#!/usr/bin/env python3
import argparse
import json
import mimetypes
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
CLI_PATH = PROJECT_ROOT / "build" / "examples" / "zi_wei_web_cli"


class ZhouYiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def do_POST(self):
        if self.path != "/api/calculate":
            self.send_error(404)
            return

        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 64 * 1024:
                raise ValueError("请求内容大小不正确")
            payload = json.loads(self.rfile.read(size))
            birth = payload["birth"]
            target = payload["target"]
            options = payload["options"]
            arguments = [
                str(CLI_PATH),
                str(birth["year"]), str(birth["month"]), str(birth["day"]),
                str(birth["hour"]), str(birth["minute"]), "0",
                "1" if payload["gender"] == "male" else "0",
                "1" if options["trueSolarTime"] else "0",
                str(options["longitude"]), str(options.get("standardMeridian", 120)),
                str(options.get("daylightSavingMinutes", 0)),
                str(target["year"]), str(target["month"]), str(target["day"]),
                str(target["hour"]), str(target["minute"]), str(payload["age"]),
            ]
            completed = subprocess.run(
                arguments,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            response = json.loads(completed.stdout or "{}")
            status = 200 if completed.returncode == 0 else 400
            self.send_json(status, response)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": f"输入参数无效：{error}"})
        except subprocess.TimeoutExpired:
            self.send_json(504, {"error": "排盘计算超时"})
        except Exception as error:
            self.send_json(500, {"error": f"服务异常：{error}"})

    def send_json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        if self.path != "/api/calculate":
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format_string, *args):
        print(f"[web] {self.address_string()} {format_string % args}")


def main():
    parser = argparse.ArgumentParser(description="ZhouYiLab 本地网页服务")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not CLI_PATH.exists():
        raise SystemExit(f"缺少 {CLI_PATH}，请先构建 zi_wei_web_cli")
    mimetypes.add_type("text/javascript", ".js")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ZhouYiHandler)
    print(f"ZhouYiLab 页面已启动：http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
