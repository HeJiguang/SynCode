#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 - "$SCRIPT_DIR/verify-hermes-live-run.py" <<'PY'
from __future__ import annotations

import importlib.util
import json
import os
import sys


path = sys.argv[1]
spec = importlib.util.spec_from_file_location("verify_hermes_live_run", path)
if spec is None or spec.loader is None:
    raise RuntimeError("failed to load verify-hermes-live-run.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

stream = """event: tool.started
data: {"tool":"skill_view","preview":"syncode-training-plan → SKILL.md"}

event: tool.started
data: {"tool_name":"mcp__syncode__get_my_learning_profile","preview":""}

event: run.completed
data: {"output":"已做 3 题"}
"""
events = module.parse_sse_events(stream)
assert [event["event"] for event in events] == [
    "tool.started",
    "tool.started",
    "run.completed",
]
module.assert_required_tools(events)
module.assert_required_tools(
    [
        {"event": "tool.started", "tool": "skill_view", "preview": "syncode-training-plan"},
        {"event": "tool.started", "tool": "get_my_learning_profile", "preview": ""},
    ]
)

try:
    module.assert_required_tools(
        [{"event": "tool.started", "tool": "skill_view", "preview": "syncode-training-plan"}]
    )
except RuntimeError as exc:
    assert "started_tools" in str(exc)
    assert "skill_view" in str(exc)
else:
    raise AssertionError("missing MCP tool should fail")

requests = []


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit=-1):
        return self.payload


def fake_urlopen(request, timeout):
    requests.append((request, timeout))
    if request.full_url.endswith("/v1/runs"):
        return Response(b'{"run_id":"run-test"}')
    if request.full_url.endswith("/v1/runs/run-test/events"):
        return Response(stream.encode("utf-8"))
    raise AssertionError(f"unexpected URL: {request.full_url}")


os.environ.update(
    {
        "VERIFY_HERMES_USER_ID": "7",
        "HERMES_API_SERVER_KEY": "test-key",
        "HERMES_MODEL": "deepseek-test",
    }
)
module.urlopen = fake_urlopen
module.main()
body = json.loads(requests[0][0].data)
assert requests[0][0].full_url == "http://hermes:8642/p/syncode-u7/v1/runs"
assert "skill_view" in body["instructions"]
assert "get_my_learning_profile" in body["instructions"]
assert body["provider"] == "deepseek"
assert body["model"] == "deepseek-test"

print("Hermes live-run acceptance parser tests passed")
PY
