#!/usr/bin/env bash

set -euo pipefail

TARGET_FILE="${1:?target key path is required}"
RUNNER_KEY_FILE="${2:-}"
TARGET_DIR="$(dirname "${TARGET_FILE}")"
CANDIDATE_FILE="${TARGET_FILE}.candidate"

mkdir -p "${TARGET_DIR}"
rm -f "${TARGET_FILE}" "${CANDIDATE_FILE}"

install_valid_key() {
  local source_file="$1"

  # Secrets copied from Windows or web forms sometimes contain CRLF line endings.
  # Normalizing them before validation avoids opaque libcrypto errors from ssh.
  sed 's/\r$//' "${source_file}" > "${CANDIDATE_FILE}"
  chmod 600 "${CANDIDATE_FILE}"

  if ssh-keygen -y -f "${CANDIDATE_FILE}" >/dev/null 2>&1; then
    mv "${CANDIDATE_FILE}" "${TARGET_FILE}"
    return 0
  fi

  rm -f "${CANDIDATE_FILE}"
  return 1
}

if [[ -n "${RUNNER_KEY_FILE}" && -f "${RUNNER_KEY_FILE}" ]]; then
  if install_valid_key "${RUNNER_KEY_FILE}"; then
    echo "worker SSH key prepared from the runner-local key"
    exit 0
  fi
  echo "runner-local worker SSH key is invalid; trying the GitHub secret" >&2
fi

if [[ -n "${WORKER_SSH_KEY:-}" ]]; then
  SECRET_FILE="${TARGET_FILE}.secret"
  trap 'rm -f "${SECRET_FILE}" "${CANDIDATE_FILE}"' EXIT
  printf '%s\n' "${WORKER_SSH_KEY}" > "${SECRET_FILE}"
  chmod 600 "${SECRET_FILE}"
  if install_valid_key "${SECRET_FILE}"; then
    echo "worker SSH key prepared from the GitHub secret"
    exit 0
  fi
  echo "GitHub WORKER_SSH_KEY is not a valid private key" >&2
fi

echo "no valid worker SSH key is available" >&2
exit 1
