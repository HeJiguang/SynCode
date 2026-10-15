#!/usr/bin/env bash

set -euo pipefail

STACK_ENV_FILE="${1:-${STACK_ENV_FILE:-deploy/prod/env/stack.env}}"
APPROVED_HERMES_BASE_IMAGE="nousresearch/hermes-agent@sha256:861c9756ed6c558530c73d5c27860343b00c0d5efd6997a1d8ec6416c8a2b485"

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

stack_value() {
  local name="$1"
  sed -n "s/^${name}=//p" "$STACK_ENV_FILE" | tail -n 1
}

base_image="${HERMES_BASE_IMAGE:-$(stack_value HERMES_BASE_IMAGE)}"
if [[ -z "$base_image" || "$base_image" == "nousresearch/hermes-agent:latest" || "$base_image" == *"REPLACE_WITH_REVIEWED_64_HEX_DIGEST"* ]]; then
  echo "[deploy] replacing the legacy Hermes base image with the approved immutable digest"
  base_image="$APPROVED_HERMES_BASE_IMAGE"
fi
if [[ ! "${base_image}" =~ @sha256:[0-9a-fA-F]{64}$ ]]; then
  echo "HERMES_BASE_IMAGE must be pinned to an approved @sha256 digest." >&2
  exit 1
fi

{
  echo "HERMES_IMAGE=syncode/hermes:sha-REPLACE_ME"
  echo "HERMES_BASE_IMAGE=${base_image}"
  echo "HERMES_MODEL=${HERMES_MODEL:-deepseek-chat}"
  echo "HERMES_DEEPSEEK_API_KEY=${HERMES_DEEPSEEK_API_KEY}"
  echo "SYNCODE_HERMES_API_KEY=${SYNCODE_HERMES_API_KEY}"
  echo "SYNCODE_HERMES_SESSION_SECRET=${SYNCODE_HERMES_SESSION_SECRET}"
  echo "SYNCODE_HERMES_PROVISION_KEY=${SYNCODE_HERMES_PROVISION_KEY}"
  echo "SYNCODE_MCP_SERVICE_KEY=${SYNCODE_MCP_SERVICE_KEY}"
} >> "$STACK_ENV_FILE"

echo "[deploy] Hermes stack configuration added"
