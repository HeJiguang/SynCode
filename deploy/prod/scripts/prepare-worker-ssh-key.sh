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

install_secret_key() {
  local secret_value="$1"
  local secret_name="$2"
  local secret_file="${TARGET_FILE}.${secret_name}"
  local decoded_file="${secret_file}.decoded"

  printf '%s\n' "${secret_value}" > "${secret_file}"
  chmod 600 "${secret_file}"
  if install_valid_key "${secret_file}"; then
    rm -f "${secret_file}" "${decoded_file}"
    echo "worker SSH key prepared from ${secret_name}"
    return 0
  fi

  # Some secret-management UIs store pasted multiline values with literal \n.
  printf '%s\n' "${secret_value//\\n/$'\n'}" > "${decoded_file}"
  chmod 600 "${decoded_file}"
  if install_valid_key "${decoded_file}"; then
    rm -f "${secret_file}" "${decoded_file}"
    echo "worker SSH key prepared from escaped ${secret_name}"
    return 0
  fi

  # Also accept a base64-encoded private key, a common single-line secret format.
  if printf '%s' "${secret_value}" | base64 --decode > "${decoded_file}" 2>/dev/null; then
    chmod 600 "${decoded_file}"
    if install_valid_key "${decoded_file}"; then
      rm -f "${secret_file}" "${decoded_file}"
      echo "worker SSH key prepared from base64 ${secret_name}"
      return 0
    fi
  fi

  rm -f "${secret_file}" "${decoded_file}"
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
  if install_secret_key "${WORKER_SSH_KEY}" "WORKER_SSH_KEY"; then
    exit 0
  fi
  echo "GitHub WORKER_SSH_KEY is not a valid private key" >&2
fi

if [[ -n "${WORKER_SSH_KEY_FALLBACK:-}" ]]; then
  if install_secret_key "${WORKER_SSH_KEY_FALLBACK}" "DEPLOY_SSH_KEY"; then
    exit 0
  fi
  echo "GitHub DEPLOY_SSH_KEY is not a valid private key" >&2
fi

echo "no valid worker SSH key is available" >&2
exit 1
