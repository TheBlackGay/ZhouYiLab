#!/usr/bin/env bash
set -euo pipefail

# 一键部署到 10.10.8.99。默认使用本机 ~/.ssh/config 中的 cloud-deploy-99 别名。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REMOTE_HOST="${ZHOUYILAB_DEPLOY_HOST:-cloud-deploy-99}"
REMOTE_USER="${ZHOUYILAB_DEPLOY_USER:-}"
REMOTE_DIR="${ZHOUYILAB_DEPLOY_DIR:-/home/h3c/zhouyilab}"
REMOTE_PORT="${ZHOUYILAB_DEPLOY_PORT:-8768}"
REMOTE="${REMOTE_USER:+${REMOTE_USER}@}${REMOTE_HOST}"
SSH_OPTS=(-o StrictHostKeyChecking=ask)

echo "Deploying ZhouYiLab to ${REMOTE}"
echo "  directory: ${REMOTE_DIR}"
echo "  endpoint:  http://${REMOTE_HOST}:${REMOTE_PORT}/"

ssh "${SSH_OPTS[@]}" "$REMOTE" \
  "docker version >/dev/null && docker compose version >/dev/null"
ssh "${SSH_OPTS[@]}" "$REMOTE" "mkdir -p '${REMOTE_DIR}'"

rsync -az --delete \
  --exclude '.git/' \
  --exclude '.zhouyilab/' \
  --exclude 'build/' \
  --exclude 'build_check/' \
  --exclude 'build_check_shared/' \
  --exclude 'cmake-build-*/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '*.o' \
  --exclude '*.a' \
  -e "ssh ${SSH_OPTS[*]}" \
  "${PROJECT_ROOT}/" "${REMOTE}:${REMOTE_DIR}/"

ssh "${SSH_OPTS[@]}" "$REMOTE" \
  "cd '${REMOTE_DIR}' && \
   ZHOUYILAB_PORT='${REMOTE_PORT}' docker compose up -d --build --force-recreate"

ssh "${SSH_OPTS[@]}" "$REMOTE" \
  "cd '${REMOTE_DIR}' && \
   docker compose ps && \
   curl --fail --silent --show-error http://127.0.0.1:8768/api/v1/health"

echo "Deployment completed: http://${REMOTE_HOST}:${REMOTE_PORT}/"
