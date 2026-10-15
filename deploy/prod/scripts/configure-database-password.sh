#!/usr/bin/env bash

set -euo pipefail

runtime_env_file="${1:-}"

if [[ -z "$runtime_env_file" || ! -f "$runtime_env_file" ]]; then
  echo "usage: configure-database-password.sh <runtime-env-file>" >&2
  exit 1
fi

if [[ -z "${MYSQL_APP_PASSWORD:-}" ]]; then
  echo "MYSQL_APP_PASSWORD is required" >&2
  exit 1
fi

if [[ "$MYSQL_APP_PASSWORD" == *$'\n'* || "$MYSQL_APP_PASSWORD" == *$'\r'* ]]; then
  echo "MYSQL_APP_PASSWORD must not contain newlines" >&2
  exit 1
fi

temp_env_file="$(mktemp "${runtime_env_file}.mysql.XXXXXX")"
trap 'rm -f "$temp_env_file"' EXIT

awk '!/^MYSQL_PASSWORD=/' "$runtime_env_file" > "$temp_env_file"
printf 'MYSQL_PASSWORD=%s\n' "$MYSQL_APP_PASSWORD" >> "$temp_env_file"

mv "$temp_env_file" "$runtime_env_file"
trap - EXIT

echo "[deploy] current MySQL application password added to runtime configuration"
