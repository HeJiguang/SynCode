#!/usr/bin/env python3

"""Run the live Hermes Skill and SynCode MCP deployment acceptance turn."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def parse_sse_events(event_stream: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    event_name = "message"
    data_lines: list[str] = []

    def append_event() -> None:
        nonlocal event_name, data_lines
        if not data_lines:
            event_name = "message"
            return
        try:
            payload = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            payload.setdefault("event", event_name)
            events.append(payload)
        event_name = "message"
        data_lines = []

    for raw_line in event_stream.splitlines():
        line = raw_line.rstrip("\r")
        if not line:
            append_event()
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if field == "event":
            event_name = value
        elif field == "data":
            data_lines.append(value)
    append_event()
    return events


def started_tools(events: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for event in events:
        if event.get("event") != "tool.started":
            continue
        result.append(
            {
                "tool": str(event.get("tool") or event.get("tool_name") or "")[:96],
                "preview": str(event.get("preview") or "")[:160],
            }
        )
    return result


def assert_required_tools(events: list[dict[str, Any]]) -> None:
    tools = started_tools(events)
    diagnostics = json.dumps(tools, ensure_ascii=False)
    if not any(tool["tool"] == "get_my_learning_profile" for tool in tools):
        raise RuntimeError(
            "Hermes completed without the required SynCode MCP tool call; "
            f"started_tools={diagnostics}"
        )
    if not any(
        tool["tool"] == "skill_view"
        and tool["preview"].split(" → ", 1)[0].strip() == "syncode-training-plan"
        for tool in tools
    ):
        raise RuntimeError(
            "Hermes completed without loading the required platform Skill; "
            f"started_tools={diagnostics}"
        )


def read_json(request: Request, *, timeout: float) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(256_000))
    except HTTPError as exc:
        detail = exc.read(256_000).decode("utf-8", errors="replace")
        raise RuntimeError(f"Hermes request failed with HTTP {exc.code}: {detail}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Hermes returned a non-object JSON response")
    return payload


def main() -> None:
    user_id = os.environ["VERIFY_HERMES_USER_ID"]
    profile = f"syncode-u{user_id}"
    api_key = os.environ["HERMES_API_SERVER_KEY"]
    base_url = f"http://hermes:8642/p/{profile}"
    verification_key = f"syncode-production-verification-{uuid4().hex}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Hermes-Session-Key": verification_key,
    }
    request = Request(
        f"{base_url}/v1/runs",
        data=json.dumps(
            {
                "input": "请只用一句中文报告当前学习档案中的已做题数，不要猜测工具没有返回的数据。",
                "instructions": (
                    "你正在执行 SynCode 训练计划链路的部署验收。"
                    "第一步必须调用 skill_view 加载 syncode-training-plan Skill；"
                    "第二步必须调用 get_my_learning_profile 读取当前用户学习档案。"
                    "完成这两个只读工具调用后才允许回答，不得只复述验收要求。"
                ),
                "provider": "deepseek",
                "model": os.environ.get("HERMES_MODEL", "deepseek-chat"),
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    created = read_json(request, timeout=30)
    run_id = str(created.get("run_id") or "")
    if not run_id:
        raise RuntimeError(f"Hermes did not return run_id: {created}")

    events_request = Request(
        f"{base_url}/v1/runs/{run_id}/events",
        headers={key: value for key, value in headers.items() if key != "Content-Type"},
    )
    with urlopen(events_request, timeout=240) as response:
        event_bytes = response.read(2_000_001)
    if len(event_bytes) > 2_000_000:
        raise RuntimeError("Hermes event stream exceeded the deployment acceptance limit")
    event_stream = event_bytes.decode("utf-8", errors="replace")

    events = parse_sse_events(event_stream)
    if not any(event.get("event") == "run.completed" for event in events):
        raise RuntimeError(f"Hermes run did not complete; final stream tail: {event_stream[-1200:]}")
    assert_required_tools(events)
    print(f"[verify-hermes] live run completed: {run_id}")


if __name__ == "__main__":
    main()
