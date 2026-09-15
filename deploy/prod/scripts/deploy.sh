#!/usr/bin/env bash

set -euo pipefail

STACK_NAME="${STACK_NAME:-onlineoj-prod}"
STACK_FILE="${STACK_FILE:-deploy/prod/swarm/stack.yml}"
STACK_ENV_FILE="${STACK_ENV_FILE:-deploy/prod/env/stack.env}"
RUNTIME_ENV_FILE="${RUNTIME_ENV_FILE:-deploy/prod/env/runtime.env}"
BUILD_LOCAL_IMAGES="${BUILD_LOCAL_IMAGES:-false}"
SYNC_WORKER_IMAGES="${SYNC_WORKER_IMAGES:-false}"
WORKER_SSH_KEY_FILE="${WORKER_SSH_KEY_FILE:-}"
STACK_WAIT_TIMEOUT_SECONDS="${STACK_WAIT_TIMEOUT_SECONDS:-600}"
STACK_WAIT_POLL_SECONDS="${STACK_WAIT_POLL_SECONDS:-5}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

usage() {
  cat <<EOF
Usage:
  BUILD_LOCAL_IMAGES=true \
  SYNC_WORKER_IMAGES=true \
  WORKER_SSH_KEY_FILE=/path/to/worker_id_ed25519 \
  STACK_ENV_FILE=deploy/prod/env/stack.env \
  RUNTIME_ENV_FILE=deploy/prod/env/runtime.env \
  ./deploy/prod/scripts/deploy.sh

Environment variables:
  STACK_NAME           Swarm stack name. Default: onlineoj-prod
  STACK_FILE           Stack compose file. Default: deploy/prod/swarm/stack.yml
  STACK_ENV_FILE       Env file consumed by docker stack deploy. Default: deploy/prod/env/stack.env
  RUNTIME_ENV_FILE     Runtime env file referenced by stack.yml. Default: deploy/prod/env/runtime.env
  BUILD_LOCAL_IMAGES   Build all production images locally before deploy. Default: false
  SYNC_WORKER_IMAGES   Copy worker images to the worker node before deploy. Default: false
  WORKER_SSH_KEY_FILE  Private key used when SYNC_WORKER_IMAGES=true
  STACK_WAIT_TIMEOUT_SECONDS  Maximum time to wait for Swarm convergence. Default: 600
  STACK_WAIT_POLL_SECONDS     Swarm convergence polling interval. Default: 5
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -f "$STACK_FILE" ]]; then
  echo "stack file not found: $STACK_FILE" >&2
  exit 1
fi

if [[ ! -f "$STACK_ENV_FILE" ]]; then
  echo "stack env file not found: $STACK_ENV_FILE" >&2
  exit 1
fi

if [[ ! -f "$RUNTIME_ENV_FILE" ]]; then
  echo "runtime env file not found: $RUNTIME_ENV_FILE" >&2
  exit 1
fi

load_env_file() {
  local env_file="$1"
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    export "$line"
  done < "$env_file"
}

echo "[deploy] stack name : $STACK_NAME"
echo "[deploy] stack file : $STACK_FILE"
echo "[deploy] stack env  : $STACK_ENV_FILE"
echo "[deploy] runtime env: $RUNTIME_ENV_FILE"
echo "[deploy] build images: $BUILD_LOCAL_IMAGES"
echo "[deploy] sync worker : $SYNC_WORKER_IMAGES"

load_env_file "$STACK_ENV_FILE"

cd "$REPO_ROOT"

if [[ "$BUILD_LOCAL_IMAGES" == "true" ]]; then
  STACK_ENV_FILE="$STACK_ENV_FILE" "$SCRIPT_DIR/build-images.sh"
fi

if [[ "$SYNC_WORKER_IMAGES" == "true" ]]; then
  if [[ -z "$WORKER_SSH_KEY_FILE" ]]; then
    echo "WORKER_SSH_KEY_FILE is required when SYNC_WORKER_IMAGES=true" >&2
    exit 1
  fi
  STACK_ENV_FILE="$STACK_ENV_FILE" WORKER_SSH_KEY_FILE="$WORKER_SSH_KEY_FILE" "$SCRIPT_DIR/sync-worker-images.sh"
fi

echo "[deploy] rendering stack config"
docker stack config --compose-file "$STACK_FILE" > /dev/null

docker stack deploy \
  --compose-file "$STACK_FILE" \
  --prune \
  --resolve-image never \
  --with-registry-auth \
  "$STACK_NAME"

echo "[deploy] stack deploy submitted"

STACK_NAME="$STACK_NAME" \
STACK_WAIT_TIMEOUT_SECONDS="$STACK_WAIT_TIMEOUT_SECONDS" \
STACK_WAIT_POLL_SECONDS="$STACK_WAIT_POLL_SECONDS" \
  "$SCRIPT_DIR/wait-for-stack.sh"

echo "[deploy] stack deploy converged"
