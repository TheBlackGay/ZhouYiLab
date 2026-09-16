#!/usr/bin/env bash
set -euo pipefail

# One-click deployment profile for 192.168.31.183.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REMOTE_HOST="${ZHOUYILAB_DEPLOY_HOST:-192.168.31.183}"
REMOTE_USER="${ZHOUYILAB_DEPLOY_USER:-zhongjiafengub1}"
REMOTE_DIR="${ZHOUYILAB_DEPLOY_DIR:-/opt/app/zhouyilab}"
REMOTE_NETWORK="${ZHOUYILAB_DEPLOY_NETWORK:-1panel-network}"
REMOTE_PORT="${ZHOUYILAB_DEPLOY_PORT:-8768}"
REMOTE="${REMOTE_USER}@${REMOTE_HOST}"
SSH_OPTS=(-o StrictHostKeyChecking=ask)

echo "Deploying ZhouYiLab to ${REMOTE}"
echo "  directory: ${REMOTE_DIR}"
echo "  network:   ${REMOTE_NETWORK}"
echo "  endpoint:  http://${REMOTE_HOST}:${REMOTE_PORT}/"

ssh "${SSH_OPTS[@]}" "$REMOTE" \
  "docker version >/dev/null && docker compose version >/dev/null && \
   test -n \"\$(docker network ls --format '{{.Name}}' | grep -Fx '${REMOTE_NETWORK}' || true)\" || \
   { echo 'Missing Docker network: ${REMOTE_NETWORK}' >&2; exit 1; }"

ssh "${SSH_OPTS[@]}" "$REMOTE" "mkdir -p '${REMOTE_DIR}'"

rsync -az --delete \
  --exclude '.git/' \
  --exclude 'build/' \
  --exclude 'build_check/' \
  --exclude 'build_check_shared/' \
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
   docker compose exec -T zhouyilab python3 -c \
   'import urllib.request; print(urllib.request.urlopen(\"http://127.0.0.1:8768/api/v1/health\").read().decode())'"

echo "Deployment completed: http://${REMOTE_HOST}:${REMOTE_PORT}/"
