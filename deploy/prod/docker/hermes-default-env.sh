#!/command/with-contenv sh

set -eu

hermes_home="${HERMES_HOME:-/opt/data}"
env_file="${hermes_home}/.env"
newline="$(printf '\nx')"
newline="${newline%x}"
carriage_return="$(printf '\rx')"
carriage_return="${carriage_return%x}"

for name in API_SERVER_KEY DEEPSEEK_API_KEY; do
  eval "value=\${${name}:-}"
  if [ -z "$value" ]; then
    echo "[syncode] missing required Hermes setting: ${name}" >&2
    exit 1
  fi
  case "$value" in
    *"$newline"* | *"$carriage_return"*)
      echo "[syncode] invalid newline in Hermes setting: ${name}" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$hermes_home"
umask 077
temp_file="$(mktemp "${env_file}.tmp.XXXXXX")"
trap 'rm -f "$temp_file"' EXIT HUP INT TERM

if [ -f "$env_file" ]; then
  grep -Ev '^(API_SERVER_ENABLED|API_SERVER_HOST|API_SERVER_PORT|API_SERVER_KEY|DEEPSEEK_API_KEY)=' \
    "$env_file" > "$temp_file" || true
fi

{
  printf '%s\n' "API_SERVER_ENABLED=${API_SERVER_ENABLED:-true}"
  printf '%s\n' "API_SERVER_HOST=${API_SERVER_HOST:-0.0.0.0}"
  printf '%s\n' "API_SERVER_PORT=${API_SERVER_PORT:-8642}"
  printf '%s\n' "API_SERVER_KEY=${API_SERVER_KEY}"
  printf '%s\n' "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}"
} >> "$temp_file"

chmod 600 "$temp_file"
chown "${HERMES_UID:-10000}:${HERMES_GID:-10000}" "$temp_file"
mv -f "$temp_file" "$env_file"
trap - EXIT HUP INT TERM

echo "[syncode] default Hermes profile environment synchronized"
