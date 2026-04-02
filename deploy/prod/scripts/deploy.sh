#!/usr/bin/env bash

set -euo pipefail

STACK_NAME="${STACK_NAME:-onlineoj-prod}"
STACK_FILE="${STACK_FILE:-deploy/prod/swarm/stack.yml}"
STACK_ENV_FILE="${STACK_ENV_FILE:-deploy/prod/env/stack.env}"
RUNTIME_ENV_FILE="${RUNTIME_ENV_FILE:-deploy/prod/env/runtime.env}"

usage() {
  cat <<EOF
Usage:
  STACK_NAME=onlineoj-prod STACK_ENV_FILE=deploy/prod/env/stack.env ./deploy/prod/scripts/deploy.sh

Environment variables:
  STACK_NAME      Swarm stack name. Default: onlineoj-prod
  STACK_FILE      Stack compose file. Default: deploy/prod/swarm/stack.yml
  STACK_ENV_FILE  Env file consumed by docker stack deploy. Default: deploy/prod/env/stack.env
  RUNTIME_ENV_FILE Runtime env file referenced by stack.yml. Default: deploy/prod/env/runtime.env
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

echo "[deploy] stack name : $STACK_NAME"
echo "[deploy] stack file : $STACK_FILE"
echo "[deploy] stack env  : $STACK_ENV_FILE"
echo "[deploy] runtime env: $RUNTIME_ENV_FILE"

set -a
source "$STACK_ENV_FILE"
set +a

docker stack deploy \
  --compose-file "$STACK_FILE" \
  --prune \
  --with-registry-auth \
  "$STACK_NAME"

echo "[deploy] stack deploy submitted"
