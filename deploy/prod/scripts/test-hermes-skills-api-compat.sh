#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
patcher="${repo_root}/deploy/prod/docker/patch-hermes-skills-api.py"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

api_server="${test_root}/api_server.py"
skills_tool="${test_root}/skills_tool.py"

cat > "$api_server" <<'PY'
def list_skills():
    return _find_all_skills(
                    skip_disabled=False, include_editorial=True
                )
PY
cat > "$skills_tool" <<'PY'
def _find_all_skills(*, skip_disabled=False):
    return []
PY

python3 "$patcher" "$api_server" "$skills_tool"
grep -Fq '_find_all_skills(skip_disabled=False)' "$api_server"
if grep -Fq 'include_editorial=True' "$api_server"; then
  echo "Hermes skills API compatibility patch left the unsupported argument in place" >&2
  exit 1
fi

first_hash="$(sha256sum "$api_server" | cut -d ' ' -f 1)"
python3 "$patcher" "$api_server" "$skills_tool"
second_hash="$(sha256sum "$api_server" | cut -d ' ' -f 1)"
[[ "$first_hash" == "$second_hash" ]]

cat > "$api_server" <<'PY'
def list_skills():
    return _find_all_skills(skip_disabled=False, include_editorial=True)
PY
cat > "$skills_tool" <<'PY'
def _find_all_skills(*, skip_disabled=False, include_editorial=False):
    return []
PY
new_helper_hash="$(sha256sum "$api_server" | cut -d ' ' -f 1)"
python3 "$patcher" "$api_server" "$skills_tool"
[[ "$new_helper_hash" == "$(sha256sum "$api_server" | cut -d ' ' -f 1)" ]]

cat > "$skills_tool" <<'PY'
def unrelated_function():
    return []
PY
if python3 "$patcher" "$api_server" "$skills_tool" >/dev/null 2>&1; then
  echo "Hermes skills API compatibility patch accepted an unknown helper layout" >&2
  exit 1
fi

echo "Hermes skills API compatibility test passed"
