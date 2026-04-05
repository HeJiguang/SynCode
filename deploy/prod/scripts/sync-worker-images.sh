#!/usr/bin/env bash

set -euo pipefail

STACK_ENV_FILE="${STACK_ENV_FILE:-deploy/prod/env/stack.env}"
WORKER_SSH_KEY_FILE="${WORKER_SSH_KEY_FILE:-}"
WORKER_SSH_PORT="${WORKER_SSH_PORT:-22}"

if [[ ! -f "$STACK_ENV_FILE" ]]; then
  echo "stack env file not found: $STACK_ENV_FILE" >&2
  exit 1
fi

if [[ -z "$WORKER_SSH_KEY_FILE" || ! -f "$WORKER_SSH_KEY_FILE" ]]; then
  echo "worker ssh key file not found: $WORKER_SSH_KEY_FILE" >&2
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

load_env_file "$STACK_ENV_FILE"

if [[ -z "${WORKER_SSH_HOST:-}" || -z "${WORKER_SSH_USER:-}" ]]; then
  echo "WORKER_SSH_HOST and WORKER_SSH_USER must be set in stack env" >&2
  exit 1
fi

if [[ -z "${WORKER_IMAGE_LIST:-}" ]]; then
  WORKER_IMAGE_LIST="${AGENT_IMAGE} ${JUDGE_IMAGE}"
fi

read -r -a worker_images <<< "$WORKER_IMAGE_LIST"
if [[ "${#worker_images[@]}" -eq 0 ]]; then
  echo "WORKER_IMAGE_LIST is empty" >&2
  exit 1
fi

for image in "${worker_images[@]}"; do
  if ! docker image inspect "$image" > /dev/null 2>&1; then
    echo "worker image not found locally: $image" >&2
    exit 1
  fi
done

archive="$(mktemp "${TMPDIR:-/tmp}/onlineoj-worker-images.XXXXXX.tar.gz")"
remote_archive="/tmp/$(basename "$archive")"
known_hosts_file="$(mktemp "${TMPDIR:-/tmp}/onlineoj-worker-known-hosts.XXXXXX")"
ssh_opts=(
  -i "$WORKER_SSH_KEY_FILE"
  -p "$WORKER_SSH_PORT"
  -o UserKnownHostsFile="$known_hosts_file"
  -o GlobalKnownHostsFile=/dev/null
  -o StrictHostKeyChecking=yes
  -o LogLevel=ERROR
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=8
)

cleanup() {
  rm -f "$archive"
  rm -f "$known_hosts_file"
}
trap cleanup EXIT

echo "[sync] collecting worker host key for ${WORKER_SSH_HOST}:${WORKER_SSH_PORT}"
ssh-keyscan -H -p "$WORKER_SSH_PORT" "$WORKER_SSH_HOST" > "$known_hosts_file" 2>/dev/null
if [[ ! -s "$known_hosts_file" ]]; then
  echo "failed to collect host key for ${WORKER_SSH_HOST}:${WORKER_SSH_PORT}" >&2
  exit 1
fi

echo "[sync] packaging worker images"
docker save "${worker_images[@]}" | gzip > "$archive"

echo "[sync] copying worker images to ${WORKER_SSH_USER}@${WORKER_SSH_HOST}"
scp "${ssh_opts[@]}" "$archive" "${WORKER_SSH_USER}@${WORKER_SSH_HOST}:${remote_archive}"

remote_prepare_cmd="set -euo pipefail"
for dir_var in JUDGE_HOST_USER_CODE_DIR JUDGE_HOST_USER_CODE_POOL_DIR; do
  dir_value="${!dir_var:-}"
  if [[ -n "$dir_value" ]]; then
    remote_prepare_cmd="${remote_prepare_cmd} && mkdir -p '${dir_value}'"
  fi
done

echo "[sync] preparing worker host directories"
ssh "${ssh_opts[@]}" "${WORKER_SSH_USER}@${WORKER_SSH_HOST}" "$remote_prepare_cmd"

echo "[sync] loading worker images on ${WORKER_SSH_HOST}"
ssh "${ssh_opts[@]}" "${WORKER_SSH_USER}@${WORKER_SSH_HOST}" "\
  set -euo pipefail && \
  gzip -dc '${remote_archive}' | docker load && \
  rm -f '${remote_archive}'"

echo "[sync] verifying worker images on ${WORKER_SSH_HOST}"
for image in "${worker_images[@]}"; do
  ssh "${ssh_opts[@]}" "${WORKER_SSH_USER}@${WORKER_SSH_HOST}" "docker image inspect '${image}' > /dev/null"
done

echo "[sync] worker image sync completed"
