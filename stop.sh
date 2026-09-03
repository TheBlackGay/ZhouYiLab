#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/.zhouyilab"
PID_FILE="$RUNTIME_DIR/server.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "ZhouYiLab 未运行（没有 PID 文件）。"
  exit 0
fi

pid="$(<"$PID_FILE")"
if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
  echo "PID 文件无效，已清理。" >&2
  rm -f "$PID_FILE"
  exit 1
fi

if ! kill -0 "$pid" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "ZhouYiLab 未运行，已清理过期 PID 文件。"
  exit 0
fi

command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
if [[ "$command" != *"$ROOT_DIR/web/server.py"* ]]; then
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
