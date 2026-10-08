#!/usr/bin/env bash

set -euo pipefail

STACK_ENV_FILE="${1:-${STACK_ENV_FILE:-deploy/prod/env/stack.env}}"

required=(
  HERMES_DEEPSEEK_API_KEY
  SYNCODE_HERMES_API_KEY
  SYNCODE_HERMES_SESSION_SECRET
  SYNCODE_HERMES_PROVISION_KEY
  SYNCODE_MCP_SERVICE_KEY
)

for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "missing required Hermes deployment secret: ${name}" >&2
    exit 1
  fi
  if [[ "${!name}" == *$'\n'* || "${!name}" == *$'\r'* ]]; then
    echo "Hermes deployment secret contains a newline: ${name}" >&2
    exit 1
  fi
done

if [[ ! -f "$STACK_ENV_FILE" ]]; then
  echo "stack env file not found: $STACK_ENV_FILE" >&2
  exit 1
fi

{
  echo "HERMES_IMAGE=syncode/hermes:sha-REPLACE_ME"
  echo "HERMES_BASE_IMAGE=${HERMES_BASE_IMAGE:-nousresearch/hermes-agent:latest}"
  echo "HERMES_MODEL=${HERMES_MODEL:-deepseek-chat}"
  echo "HERMES_DEEPSEEK_API_KEY=${HERMES_DEEPSEEK_API_KEY}"
  echo "SYNCODE_HERMES_API_KEY=${SYNCODE_HERMES_API_KEY}"
  echo "SYNCODE_HERMES_SESSION_SECRET=${SYNCODE_HERMES_SESSION_SECRET}"
  echo "SYNCODE_HERMES_PROVISION_KEY=${SYNCODE_HERMES_PROVISION_KEY}"
  echo "SYNCODE_MCP_SERVICE_KEY=${SYNCODE_MCP_SERVICE_KEY}"
} >> "$STACK_ENV_FILE"

echo "[deploy] Hermes stack configuration added"
