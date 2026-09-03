#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$ROOT_DIR/stop.sh" || {
  status=$?
  echo "停止旧服务失败，未继续重启。" >&2
  exit "$status"
}
"$ROOT_DIR/start.sh"
