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
pid="$(python3 -c 'import os, subprocess, sys; root, port, log_path = sys.argv[1:]; log = open(log_path, "ab", buffering=0); process = subprocess.Popen([sys.executable, os.path.join(root, "web", "server.py"), "--port", port], cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True); print(process.pid)' "$ROOT_DIR" "$PORT" "$LOG_FILE")"
echo "$pid" >"$PID_FILE"

sleep 0.2
if ! kill -0 "$pid" 2>/dev/null; then
  echo "ZhouYiLab 启动失败，请查看日志：$LOG_FILE" >&2
  rm -f "$PID_FILE"
  exit 1
fi

echo "ZhouYiLab 已启动，PID=${pid}，地址：http://127.0.0.1:${PORT}"
echo "日志：$LOG_FILE"
