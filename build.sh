#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${ZHOUYILAB_BUILD_DIR:-$ROOT_DIR/build}"

cmake -S "$ROOT_DIR" -B "$BUILD_DIR"
build_args=(
  --build "$BUILD_DIR"
  --target
  zi_wei_web_cli
  qi_men_web_cli
  ba_zi_web_cli
  liu_yao_web_cli
  da_liu_ren_web_cli
)
if [[ -n "${ZHOUYILAB_BUILD_JOBS:-}" ]]; then
  build_args+=(--parallel "$ZHOUYILAB_BUILD_JOBS")
fi
cmake "${build_args[@]}"

echo "ZhouYiLab 网页计算引擎构建完成：$BUILD_DIR/examples"
