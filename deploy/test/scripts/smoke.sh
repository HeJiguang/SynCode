#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${TEST_BASE_URL:?TEST_BASE_URL is required}"
BASE_URL="${BASE_URL%/}"
MAX_ATTEMPTS="${SMOKE_MAX_ATTEMPTS:-24}"

request_status() {
  local path="$1"
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --connect-timeout 5 --max-time 15 "${BASE_URL}${path}"
}

wait_for_status() {
  local path="$1"
  local expected_statuses="$2"
  local attempt status
  for ((attempt = 1; attempt <= MAX_ATTEMPTS; attempt++)); do
    status="$(request_status "$path" || true)"
    if [[ " $expected_statuses " == *" $status "* ]]; then
      echo "[smoke] ${path}: ${status}"
      return 0
    fi
    echo "[smoke] waiting for ${path}: got ${status:-connection-error}, expected one of ${expected_statuses} (${attempt}/${MAX_ATTEMPTS})"
    sleep 5
  done
  return 1
}

wait_for_status "/" "200"
wait_for_status "/app/login" "200"
wait_for_status "/admin/login" "200"
wait_for_status "/app/api/trusted-exams/exams/1/access" "307 401"

echo "[smoke] test environment is serving all Phase 1 entry points"
