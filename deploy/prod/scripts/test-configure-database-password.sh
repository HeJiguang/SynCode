#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT

runtime_env_file="$temp_dir/runtime.env"
cat > "$runtime_env_file" <<'EOF'
MYSQL_HOST=mysql
MYSQL_PASSWORD=old-password
REDIS_PASSWORD=keep-me
MYSQL_PASSWORD=stale-duplicate
EOF

expected_password='new:P@ss/with symbols & spaces?'
MYSQL_APP_PASSWORD="$expected_password" \
  "$SCRIPT_DIR/configure-database-password.sh" "$runtime_env_file"

[[ "$(grep -c '^MYSQL_PASSWORD=' "$runtime_env_file")" == "1" ]]
grep -Fqx "MYSQL_PASSWORD=${expected_password}" "$runtime_env_file"
grep -Fqx 'MYSQL_HOST=mysql' "$runtime_env_file"
grep -Fqx 'REDIS_PASSWORD=keep-me' "$runtime_env_file"
! grep -Fq 'old-password' "$runtime_env_file"
! grep -Fq 'stale-duplicate' "$runtime_env_file"

echo "configure-database-password tests passed"
