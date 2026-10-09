#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
script="${repo_root}/deploy/prod/docker/hermes-default-env.sh"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

cat > "${test_root}/.env" <<'EOF'
KEEP_ME=unchanged
API_SERVER_KEY=stale
API_SERVER_PORT=9999
DEEPSEEK_API_KEY=stale
EOF

run_sync() {
  HERMES_HOME="$test_root" \
  HERMES_UID="$(id -u)" \
  HERMES_GID="$(id -g)" \
  API_SERVER_ENABLED=true \
  API_SERVER_HOST=0.0.0.0 \
  API_SERVER_PORT=8642 \
  API_SERVER_KEY=0123456789abcdef \
  DEEPSEEK_API_KEY=deepseek-test-key \
    "$script"
}

run_sync
first_hash="$(sha256sum "${test_root}/.env" | cut -d ' ' -f 1)"
run_sync
second_hash="$(sha256sum "${test_root}/.env" | cut -d ' ' -f 1)"
file_mode="$(stat -c '%a' "${test_root}/.env" 2>/dev/null || stat -f '%Lp' "${test_root}/.env")"

[[ "$first_hash" == "$second_hash" ]]
[[ "$file_mode" == "600" ]]
[[ "$(grep -c '^KEEP_ME=unchanged$' "${test_root}/.env")" == "1" ]]
[[ "$(grep -c '^API_SERVER_KEY=0123456789abcdef$' "${test_root}/.env")" == "1" ]]
[[ "$(grep -c '^API_SERVER_HOST=0.0.0.0$' "${test_root}/.env")" == "1" ]]
[[ "$(grep -c '^API_SERVER_PORT=8642$' "${test_root}/.env")" == "1" ]]
[[ "$(grep -c '^DEEPSEEK_API_KEY=deepseek-test-key$' "${test_root}/.env")" == "1" ]]

if HERMES_HOME="$test_root" DEEPSEEK_API_KEY=deepseek-test-key "$script" >/dev/null 2>&1; then
  echo "Hermes default environment accepted a missing API_SERVER_KEY" >&2
  exit 1
fi

echo "Hermes default profile environment test passed"
