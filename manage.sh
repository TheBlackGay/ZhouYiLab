#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "用法：$0 {build|start|restart|stop|status}"
}

case "${1:-}" in
  build)   exec "$ROOT_DIR/build.sh" ;;
  start)   exec "$ROOT_DIR/start.sh" ;;
  restart) exec "$ROOT_DIR/restart.sh" ;;
  stop)    exec "$ROOT_DIR/stop.sh" ;;
  status)
    port="${ZHOUYILAB_PORT:-8768}"
    pid_file="$ROOT_DIR/.zhouyilab/server.pid"
    if [[ -f "$pid_file" ]] && pid="$(<"$pid_file")" && [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
      echo "ZhouYiLab 进程运行中，PID=${pid}，端口=${port}"
    elif lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "端口 $port 被占用，但 PID 文件未指向有效的 ZhouYiLab 进程。"
      exit 1
    else
      echo "ZhouYiLab 未运行。"
      exit 1
    fi
    ;;
  *) usage >&2; exit 2 ;;
esac
