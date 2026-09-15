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

demo_headers="$(curl --silent --show-error --dump-header - --output /dev/null \
  --request POST --connect-timeout 5 --max-time 15 "${BASE_URL}/app/api/auth/demo")"
if [[ "$demo_headers" != *"syncode_demo_session=1"* ]]; then
  echo "[smoke] demo login did not issue a session cookie" >&2
  exit 1
fi

demo_page="$(curl --silent --show-error --header 'Cookie: syncode_demo_session=1' \
  --connect-timeout 5 --max-time 15 "${BASE_URL}/app")"
if [[ "$demo_page" != *"完成两数之和并总结"* ]]; then
  echo "[smoke] demo session did not reach the test-data dashboard" >&2
  exit 1
fi
echo "[smoke] demo login: 200 with isolated test-data session"

wait_for_status "/app/api/trusted-exams/exams/1/access" "307 401"
wait_for_status "/friend/exam/1/access" "200"

echo "[smoke] test environment is serving all Phase 1 entry points"
