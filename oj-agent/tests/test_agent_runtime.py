from dataclasses import replace
import json
from pathlib import Path

import httpx
import pytest

from app.agent_runtime.base import AgentRunRequest, AgentRunResult, AgentRuntime, AgentRuntimeError
from app.agent_runtime.fallback import FallbackAgentRuntime
from app.agent_runtime.hermes import HermesAgentRuntime
from app.agent_runtime.session_store import HermesSessionStore
from app.core.config import load_settings


def _hermes_settings(tmp_path: Path, monkeypatch, **changes):
    monkeypatch.setattr("app.core.config._resolve_default_nacos_ip", lambda: "127.0.0.1")
    settings = replace(
        load_settings(),
        agent_runtime_provider="hermes",
        hermes_base_url="http://hermes.test:8642",
        hermes_api_key="sidecar-test-key",
        hermes_provider="deepseek",
        hermes_chat_model="deepseek-v4-pro",
        hermes_training_model="deepseek-v4-pro",
        hermes_request_timeout_seconds=1.0,
        hermes_run_timeout_seconds=1.0,
        hermes_poll_interval_seconds=0.01,
        runtime_data_dir=str(tmp_path),
    )
    return replace(settings, **changes)


def _request(*, trace_id: str = "trace-1") -> AgentRunRequest:
    return AgentRunRequest(
        system_prompt="Return JSON.",
        user_prompt="Help me understand this problem.",
        capability="chat",
        user_id="user-7",
        trace_id=trace_id,
        conversation_id="question-42",
    )


def test_hermes_runtime_creates_polls_and_resumes_session(tmp_path: Path, monkeypatch):
    post_bodies: list[dict] = []
    poll_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal poll_count
        assert request.headers["Authorization"] == "Bearer sidecar-test-key"
        assert request.headers["X-Hermes-Session-Key"].startswith("syncode:")
        assert request.headers["Idempotency-Key"].startswith("syncode-")

        if request.method == "POST" and request.url.path == "/v1/runs":
            body = json.loads(request.content)
            post_bodies.append(body)
            return httpx.Response(202, json={"run_id": f"run-{len(post_bodies)}", "status": "started"})
        if request.method == "GET" and request.url.path.startswith("/v1/runs/"):
            poll_count += 1
            if poll_count == 1:
                return httpx.Response(200, json={"status": "running", "session_id": "session-live-1"})
            session_id = "session-live-1" if len(post_bodies) == 1 else "session-live-2"
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "session_id": session_id,
                    "model": "deepseek-v4-pro",
                    "output": '```json\n{"answer":"先分析边界条件"}\n```',
                    "runtime": {"provider": "deepseek", "model": "deepseek-v4-pro"},
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        base_url="http://hermes.test:8642/v1",
        transport=httpx.MockTransport(handler),
    )
    settings = _hermes_settings(tmp_path, monkeypatch)

    runtime = HermesAgentRuntime(settings, http_client=client)
    first_result, first_payload = runtime.generate_json(_request())

    assert first_payload == {"answer": "先分析边界条件"}
    assert first_result.remote_run_id == "run-1"
    assert first_result.session_id == "session-live-1"
    assert "session_id" not in post_bodies[0]

    resumed_runtime = HermesAgentRuntime(
        settings,
        http_client=client,
        session_store=HermesSessionStore(tmp_path),
    )
    second_result = resumed_runtime.generate(_request(trace_id="trace-2"))

    assert post_bodies[1]["session_id"] == "session-live-1"
    assert post_bodies[1]["provider"] == "deepseek"
    assert post_bodies[1]["model"] == "deepseek-v4-pro"
    assert second_result.session_id == "session-live-2"
    assert HermesSessionStore(tmp_path).get("user-7", "question-42") == "session-live-2"
    client.close()


def test_hermes_runtime_reports_terminal_failure(tmp_path: Path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(202, json={"run_id": "run-failed", "status": "started"})
        return httpx.Response(200, json={"status": "failed", "error": "provider unavailable"})

    client = httpx.Client(base_url="http://hermes.test:8642/v1", transport=httpx.MockTransport(handler))
    runtime = HermesAgentRuntime(_hermes_settings(tmp_path, monkeypatch), http_client=client)

    with pytest.raises(AgentRuntimeError, match="provider unavailable"):
        runtime.generate(_request())
    client.close()


def test_hermes_runtime_stops_timed_out_run(tmp_path: Path, monkeypatch):
    stopped_runs: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/runs":
            return httpx.Response(202, json={"run_id": "run-timeout", "status": "started"})
        if request.method == "GET":
            return httpx.Response(200, json={"status": "running"})
        if request.method == "POST" and request.url.path.endswith("/stop"):
            stopped_runs.append(request.url.path)
            return httpx.Response(200, json={"status": "stopping"})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(base_url="http://hermes.test:8642/v1", transport=httpx.MockTransport(handler))
    runtime = HermesAgentRuntime(
        _hermes_settings(tmp_path, monkeypatch, hermes_run_timeout_seconds=0.0),
        http_client=client,
    )

    with pytest.raises(AgentRuntimeError, match="运行超时"):
        runtime.generate(_request())
    assert stopped_runs == ["/v1/runs/run-timeout/stop"]
    client.close()


def test_hermes_runtime_denies_host_tool_and_continues_run(tmp_path: Path, monkeypatch):
    approval_bodies: list[dict] = []
    approval_resolved = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal approval_resolved
        if request.method == "POST" and request.url.path == "/v1/runs":
            return httpx.Response(202, json={"run_id": "run-approval", "status": "started"})
        if request.method == "GET" and not approval_resolved:
            return httpx.Response(
                200,
                json={
                    "status": "waiting_for_approval",
                    "session_id": "session-approval",
                    "approval": {
                        "request_id": "approval-request-1",
                        "command": "git clone https://github.com/example/project",
                        "description": "download a repository",
                    },
                },
            )
        if request.method == "POST" and request.url.path.endswith("/approval"):
            approval_bodies.append(json.loads(request.content))
            approval_resolved = True
            return httpx.Response(200, json={"resolved": 1})
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "session_id": "session-approval",
                    "output": '{"answer":"该下载需要通过 SynCode 的受控 GitHub 工具。"}',
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(base_url="http://hermes.test:8642/v1", transport=httpx.MockTransport(handler))
    runtime = HermesAgentRuntime(_hermes_settings(tmp_path, monkeypatch), http_client=client)

    result = runtime.generate(_request())

    assert approval_bodies == [{"choice": "deny", "request_id": "approval-request-1"}]
    assert result.tool_decisions[0]["tool_name"] == "host.shell"
    assert result.tool_decisions[0]["decision"] == "BLOCK"
    assert "受控 GitHub 工具" in result.text
    client.close()


def test_hermes_runtime_stops_approval_without_request_id(tmp_path: Path, monkeypatch):
    stopped_runs: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/runs":
            return httpx.Response(202, json={"run_id": "run-approval", "status": "started"})
        if request.method == "GET":
            return httpx.Response(200, json={"status": "waiting_for_approval", "approval": {}})
        if request.method == "POST" and request.url.path.endswith("/stop"):
            stopped_runs.append(request.url.path)
            return httpx.Response(200, json={"status": "stopping"})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(base_url="http://hermes.test:8642/v1", transport=httpx.MockTransport(handler))
    runtime = HermesAgentRuntime(_hermes_settings(tmp_path, monkeypatch), http_client=client)

    with pytest.raises(AgentRuntimeError, match="缺少 request_id"):
        runtime.generate(_request())
    assert stopped_runs == ["/v1/runs/run-approval/stop"]
    client.close()


class _StubRuntime(AgentRuntime):
    def __init__(self, name: str, *, result: AgentRunResult | None = None, error: str | None = None) -> None:
        self._name = name
        self.result = result
        self.error = error
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return True

    def model_name(self, capability: str) -> str:
        return f"{self._name}-model"

    def generate(self, request: AgentRunRequest) -> AgentRunResult:
        self.calls += 1
        if self.error:
            raise AgentRuntimeError(self.error)
        assert self.result is not None
        return self.result


def test_fallback_runtime_uses_direct_when_hermes_fails():
    primary = _StubRuntime("hermes", error="sidecar unavailable")
    fallback = _StubRuntime(
        "direct",
        result=AgentRunResult(
            text='{"answer":"fallback"}',
            runtime_name="direct",
            provider="deepseek",
            model_name="deepseek-v4-pro",
        ),
    )

    result, payload = FallbackAgentRuntime(primary, fallback).generate_json(_request())

    assert payload == {"answer": "fallback"}
    assert result.runtime_name == "direct"
    assert result.fallback_from == "hermes"
    assert primary.calls == 1
    assert fallback.calls == 1


def test_fallback_runtime_uses_direct_for_invalid_primary_json():
    primary = _StubRuntime(
        "hermes",
        result=AgentRunResult(
            text="not-json",
            runtime_name="hermes",
            provider="deepseek",
            model_name="deepseek-v4-pro",
        ),
    )
    fallback = _StubRuntime(
        "direct",
        result=AgentRunResult(
            text='{"answer":"fallback"}',
            runtime_name="direct",
            provider="deepseek",
            model_name="deepseek-v4-pro",
        ),
    )

    result, payload = FallbackAgentRuntime(primary, fallback).generate_json(_request())

    assert payload == {"answer": "fallback"}
    assert result.fallback_from == "hermes"
