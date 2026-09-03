#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${ZHOUYILAB_PORT:-8768}"
RUNTIME_DIR="$ROOT_DIR/.zhouyilab"
PID_FILE="$RUNTIME_DIR/server.pid"
LOG_FILE="$RUNTIME_DIR/server.log"

mkdir -p "$RUNTIME_DIR"

if [[ -f "$PID_FILE" ]]; then
  pid="$(<"$PID_FILE")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    echo "ZhouYiLab 已在运行，PID=${pid}，地址：http://127.0.0.1:${PORT}"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

port_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [[ -n "$port_pid" ]]; then
  echo "端口 ${PORT} 已被占用（PID=${port_pid}），未启动 ZhouYiLab。" >&2
  exit 1
fi

cd "$ROOT_DIR"
nohup python3 "$ROOT_DIR/web/server.py" --port "$PORT" >"$LOG_FILE" 2>&1 &
pid=$!
echo "$pid" >"$PID_FILE"

sleep 0.2
if ! kill -0 "$pid" 2>/dev/null; then
  echo "ZhouYiLab 启动失败，请查看日志：$LOG_FILE" >&2
  rm -f "$PID_FILE"
  exit 1
fi

echo "ZhouYiLab 已启动，PID=${pid}，地址：http://127.0.0.1:${PORT}"
echo "日志：$LOG_FILE"
