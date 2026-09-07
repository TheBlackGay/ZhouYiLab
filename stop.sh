#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${ZHOUYILAB_PORT:-8768}"
RUNTIME_DIR="$ROOT_DIR/.zhouyilab"
PID_FILE="$RUNTIME_DIR/server.pid"

is_project_server() {
  local candidate="$1"
  local candidate_command candidate_cwd
  candidate_command="$(ps -p "$candidate" -o command= 2>/dev/null || true)"
  candidate_cwd="$(lsof -a -p "$candidate" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)"
  [[ "$candidate_command" == *"$ROOT_DIR/web/server.py"* ]] || \
    [[ "$candidate_command" == *"web/server.py"* && "$candidate_cwd" == "$ROOT_DIR" ]]
}

if [[ ! -f "$PID_FILE" ]]; then
  pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
  if [[ -z "$pid" ]]; then
    echo "ZhouYiLab 未运行（没有 PID 文件）。"
    exit 0
  fi
  if ! is_project_server "$pid"; then
    echo "端口 ${PORT} 已被其他进程占用（PID=${pid}），未停止。" >&2
    exit 1
  fi
  echo "$pid" >"$PID_FILE"
fi

pid="$(<"$PID_FILE")"
if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
  echo "PID 文件无效，已清理。" >&2
  rm -f "$PID_FILE"
  exit 1
fi

if ! kill -0 "$pid" 2>/dev/null; then
  rm -f "$PID_FILE"
  port_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
  if [[ -n "$port_pid" ]]; then
    if is_project_server "$port_pid"; then
      pid="$port_pid"
    else
      echo "ZhouYiLab 未运行，已清理过期 PID 文件；端口 ${PORT} 被其他进程占用。"
      exit 0
    fi
  else
    echo "ZhouYiLab 未运行，已清理过期 PID 文件。"
    exit 0
  fi
fi

if ! is_project_server "$pid"; then
  echo "PID=${pid} 不是本项目 web/server.py，未停止。" >&2
  exit 1
fi

kill "$pid"
for _ in {1..20}; do
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "ZhouYiLab 已停止。"
    exit 0
  fi
  sleep 0.1
done

echo "服务未在预期时间内退出，请检查 PID=${pid}。" >&2
exit 1
