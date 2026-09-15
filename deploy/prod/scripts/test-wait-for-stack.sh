#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT

mkdir -p "$TEST_DIR/bin"
cat > "$TEST_DIR/bin/docker" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

case "${1:-}:${2:-}" in
  stack:services)
    if [[ "$*" == *"{{.Name}}|{{.Replicas}}"* ]]; then
      echo "onlineoj-test_oj-runtime|${MOCK_REPLICAS:-1/1}"
    elif [[ "$*" == *"{{.Name}}"* ]]; then
      echo "onlineoj-test_oj-runtime"
    else
      echo "NAME MODE REPLICAS"
    fi
    ;;
  service:inspect)
    printf '%s\n' "${MOCK_UPDATE_STATE:-completed}"
    ;;
  service:ps)
    echo "ID NAME IMAGE NODE DESIRED STATE CURRENT STATE ERROR PORTS"
    ;;
  *)
    echo "unexpected docker invocation: $*" >&2
    exit 2
    ;;
esac
MOCK
chmod +x "$TEST_DIR/bin/docker"

run_wait() {
  env \
    PATH="$TEST_DIR/bin:$PATH" \
    STACK_NAME=onlineoj-test \
    STACK_WAIT_TIMEOUT_SECONDS=0 \
    STACK_WAIT_POLL_SECONDS=1 \
    "$@" \
    bash "$SCRIPT_DIR/wait-for-stack.sh"
}

ready_output="$(run_wait MOCK_REPLICAS=1/1 MOCK_UPDATE_STATE=completed)"
[[ "$ready_output" == *"stack onlineoj-test converged"* ]]

if run_wait MOCK_REPLICAS=1/1 MOCK_UPDATE_STATE=updating >/dev/null 2>&1; then
  echo "updating service should not be accepted as converged" >&2
  exit 1
fi

if run_wait MOCK_REPLICAS=0/1 MOCK_UPDATE_STATE=completed >/dev/null 2>&1; then
  echo "missing replicas should not be accepted as converged" >&2
  exit 1
fi

if run_wait MOCK_REPLICAS=1/1 MOCK_UPDATE_STATE=paused >/dev/null 2>&1; then
  echo "paused update should fail immediately" >&2
  exit 1
fi

echo "wait-for-stack tests passed"
