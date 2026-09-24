#!/usr/bin/env bash

set -euo pipefail

runtime_env_file="${1:-}"

if [[ -z "$runtime_env_file" || ! -f "$runtime_env_file" ]]; then
  echo "usage: configure-login-mail.sh <runtime-env-file>" >&2
  exit 1
fi

required_vars=(
  LOGIN_MAIL_HOST
  LOGIN_MAIL_PORT
  LOGIN_MAIL_USERNAME
  LOGIN_MAIL_PASSWORD
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "production login mail configuration is missing ${var_name}" >&2
    exit 1
  fi
done

if [[ ! "$LOGIN_MAIL_PORT" =~ ^[0-9]+$ ]]; then
  echo "LOGIN_MAIL_PORT must be numeric" >&2
  exit 1
fi

login_mail_from="${LOGIN_MAIL_FROM:-$LOGIN_MAIL_USERNAME}"
login_mail_subject="${LOGIN_MAIL_SUBJECT:-SynCode 登录验证码}"

case "$LOGIN_MAIL_PORT" in
  465)
    login_mail_starttls=false
    login_mail_starttls_required=false
    login_mail_ssl_enable=true
    ;;
  *)
    login_mail_starttls=true
    login_mail_starttls_required=true
    login_mail_ssl_enable=false
    ;;
esac

temp_env_file="$(mktemp "${runtime_env_file}.mail.XXXXXX")"
trap 'rm -f "$temp_env_file"' EXIT

awk '!/^MAIL_(IS_SEND|HOST|PORT|USERNAME|PASSWORD|FROM|SUBJECT|AUTH|STARTTLS|STARTTLS_REQUIRED|SSL_ENABLE|SSL_PROTOCOLS|CODE_EXPIRATION|SEND_LIMIT)=/' \
  "$runtime_env_file" > "$temp_env_file"

{
  printf 'MAIL_IS_SEND=true\n'
  printf 'MAIL_HOST=%s\n' "$LOGIN_MAIL_HOST"
  printf 'MAIL_PORT=%s\n' "$LOGIN_MAIL_PORT"
  printf 'MAIL_USERNAME=%s\n' "$LOGIN_MAIL_USERNAME"
  printf 'MAIL_PASSWORD=%s\n' "$LOGIN_MAIL_PASSWORD"
  printf 'MAIL_FROM=%s\n' "$login_mail_from"
  printf 'MAIL_SUBJECT=%s\n' "$login_mail_subject"
  printf 'MAIL_AUTH=true\n'
  printf 'MAIL_STARTTLS=%s\n' "$login_mail_starttls"
  printf 'MAIL_STARTTLS_REQUIRED=%s\n' "$login_mail_starttls_required"
  printf 'MAIL_SSL_ENABLE=%s\n' "$login_mail_ssl_enable"
  printf 'MAIL_SSL_PROTOCOLS=TLSv1.2\n'
  printf 'MAIL_CODE_EXPIRATION=5\n'
  printf 'MAIL_SEND_LIMIT=3\n'
} >> "$temp_env_file"

mv "$temp_env_file" "$runtime_env_file"
trap - EXIT

echo "[deploy] production login email delivery enabled via ${LOGIN_MAIL_HOST}:${LOGIN_MAIL_PORT}"
