#!/usr/bin/env bash
# run.sh — build / up / down / logs / shell / rebuild
set -euo pipefail

IMAGE="${IMAGE:-whisper-api}"
TAG="${TAG:-latest}"
CONTAINER="${CONTAINER:-whisper-api}"
HOST_PORT="${HOST_PORT:-8000}"
ENV_FILE="${ENV_FILE:-./server/.env}"

ensure_dirs() {
  mkdir -p "$(pwd)/var/cache"
  [[ -f "$ENV_FILE" ]] || { echo "ERROR: $ENV_FILE が見つかりません"; exit 1; }
}

build() {
  docker build -f Dockerfile.dev -t "${IMAGE}:${TAG}" .
}

up() {
  ensure_dirs
  # 既存の同名コンテナがあれば一旦消す
  if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
  fi
  docker run -d --name "${CONTAINER}" \
    -p "${HOST_PORT}:8000" \
    -v "$(pwd)/server:/server" \
    -v "$(pwd)/var/cache:/cache" \
    -v "$(pwd)/var/data:/data" \
    -v "$(pwd)/var/logs:/logs" \
    --env-file "${ENV_FILE}" \
    --restart unless-stopped \
    "${IMAGE}:${TAG}" \
    sh -lc "uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude 'var/*'"
  echo "UP: http://localhost:${HOST_PORT}"
}

down() {
  docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
  echo "DOWN: ${CONTAINER}"
}

logs() {
  docker logs -f "${CONTAINER}"
}

shell() {
  docker exec -it "${CONTAINER}" bash
}

py() {
  docker exec -it "${CONTAINER}" python "$@"
}

case "${1:-}" in
  build)   build ;;
  up)      up ;;
  down)    down ;;
  logs)    logs ;;
  shell|sh) shell ;;
  py)      shift; py "$@" ;;
  rebuild) build; down; up ;;
  *) echo "usage: $0 {build|up|down|logs|shell|py|rebuild}"; exit 1 ;;
esac
