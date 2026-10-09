#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
patcher="${repo_root}/deploy/prod/docker/patch-hermes-governance-api.py"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

api_server="${test_root}/api_server.py"
write_approval="${test_root}/write_approval.py"
memory_tool="${test_root}/memory_tool.py"
approval="${test_root}/approval.py"
context_compressor="${test_root}/context_compressor.py"
approval_context="${test_root}/approval_context.py"
approval_wait="${test_root}/approval_wait.py"
session_messages="${test_root}/session_messages.py"

cat > "$api_server" <<'PY'
from gateway.platforms import api_server_runs as _api_runs

class APIServerAdapter:
    def _http_route_table(self):
        routes = []
        routes.extend(_api_runs._http_routes(self))
        return routes
PY
cat > "$write_approval" <<'PY'
def list_pending(): pass
def get_pending(): pass
def discard_pending(): pass
PY
cat > "$memory_tool" <<'PY'
def load_on_disk_store(): pass
def apply_memory_pending(): pass
PY
cat > "$approval" <<'PY'
def _gateway_notify_cb(): pass
def resolve_gateway_approval(): pass
PY

cat > "$context_compressor" <<'PY'
class ContextCompressor:
    def __init__(self): pass
    def compress(self): pass
    def _generate_summary(self): pass
    def _strip_summary_prefix(self): pass
    def _with_summary_prefix(self): pass
PY
cat > "$approval_context" <<'PY'
def get_current_session_key(): pass
PY
cat > "$approval_wait" <<'PY'
def _await_gateway_decision(): pass
PY
cat > "$session_messages" <<'PY'
class SessionMessagesMixin:
    def get_active_message_watermark(self): pass
PY

compat_args=(
  "$api_server"
  "$write_approval"
  "$memory_tool"
  "$approval"
  "$context_compressor"
  "$approval_context"
  "$approval_wait"
  "$session_messages"
)

python3 "$patcher" "${compat_args[@]}"
grep -Fq 'from gateway.platforms import api_server_syncode_governance as _syncode_governance' "$api_server"
grep -Fq 'routes.extend(_syncode_governance._http_routes(self))' "$api_server"

first_hash="$(sha256sum "$api_server" | cut -d ' ' -f 1)"
python3 "$patcher" "${compat_args[@]}"
[[ "$first_hash" == "$(sha256sum "$api_server" | cut -d ' ' -f 1)" ]]

sed -i.bak '/def discard_pending/d' "$write_approval"
if python3 "$patcher" "${compat_args[@]}" >/dev/null 2>&1; then
  echo "Hermes governance patch accepted an incompatible memory API" >&2
  exit 1
fi

sed -i.bak '/def get_active_message_watermark/d' "$session_messages"
if python3 "$patcher" "${compat_args[@]}" >/dev/null 2>&1; then
  echo "Hermes governance patch accepted an incompatible context engine API" >&2
  exit 1
fi

echo "Hermes governance API compatibility test passed"
