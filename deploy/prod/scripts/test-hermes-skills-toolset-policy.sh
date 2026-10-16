#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
verifier="${repo_root}/deploy/prod/docker/verify-hermes-skills-toolset.py"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

allowed="${test_root}/allowed.py"
cat > "$allowed" <<'PY'
registry.register(name="skills_list", toolset="skills", schema={})
registry.register(name="skill_view", toolset="skills", schema={})
registry.register(name="terminal", toolset="terminal", schema={})
PY
python3 "$verifier" "$allowed"

expanded="${test_root}/expanded.py"
cat > "$expanded" <<'PY'
registry.register(name="skills_list", toolset="skills", schema={})
registry.register(name="skill_view", toolset="skills", schema={})
registry.register(name="skill_install", toolset="skills", schema={})
PY
if python3 "$verifier" "$expanded" >/dev/null 2>&1; then
  echo "Hermes skills toolset verifier accepted a write-capable tool" >&2
  exit 1
fi

echo "Hermes skills toolset policy test passed"
