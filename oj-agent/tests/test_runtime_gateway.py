from __future__ import annotations

import json

from fastapi.testclient import TestClient
import pytest

from app.runtime_gateway.adapters import (
    RuntimeAdapterError,
    RuntimeContext,
    RuntimeResponse,
    SynCodeV1RuntimeAdapter,
    create_adapter,
    translate_hermes_messages,
    translate_hermes_run_body,
)
from app.runtime_gateway.ids import PublicIdError, decode_public_id, encode_public_id
from app.runtime_gateway.ledger import _status_from_event
from app.runtime_gateway.registry import RegistryError, RuntimeConflictError, RuntimeRegistry, RuntimeSpec
from app.runtime_gateway.server import GatewaySettings, _rewrite_sse_frame, create_app


def _spec(name: str) -> RuntimeSpec:
    return RuntimeSpec(adapter="hermes", base_url=f"http://runtime-{name}", api_key=f"key-{name}")


def test_public_ids_round_trip_and_reject_wrong_resource_kind():
    public_id = encode_public_id("session", "hermes-v2", "native/session:你好")
    assert decode_public_id(public_id, "session") == ("hermes-v2", "native/session:你好")
    with pytest.raises(PublicIdError):
        decode_public_id(public_id, "run")
    with pytest.raises(PublicIdError):
        decode_public_id("rts.Hermes.bad", "session")


def test_only_run_events_can_change_the_durable_run_status():
    assert _status_from_event("run.completed", {"status": "completed"}) == "completed"
    assert _status_from_event("tool.completed", {"status": "completed"}) is None
    assert _status_from_event("subagent.complete", {"status": "failed"}) is None


def test_registry_is_atomic_immutable_and_reloadable(tmp_path):
    path = tmp_path / "runtime" / "registry.json"
    first = RuntimeRegistry(path, "runtime-a", _spec("a"))
    second = RuntimeRegistry(path, "runtime-a", _spec("a"))

    assert path.stat().st_mode & 0o777 == 0o600
    assert first.register("runtime-b", _spec("b")) is True
    assert first.register("runtime-b", _spec("b")) is False
    with pytest.raises(RuntimeConflictError):
        first.register("runtime-b", _spec("replacement"))

    assert second.snapshot().runtimes["runtime-b"] == _spec("b")
    assert second.activate("runtime-b") is True
    assert first.snapshot().active == "runtime-b"
    assert list(path.parent.glob(".registry.json.*")) == []
    assert RuntimeRegistry(path, "unused", None).snapshot().active == "runtime-b"

    with pytest.raises(RegistryError, match="default Runtime"):
        RuntimeRegistry(tmp_path / "empty" / "registry.json", "missing", None)


def test_protocol_native_runtime_is_pluggable_without_a_hermes_profile():
    spec = RuntimeSpec(adapter="syncode-v1", base_url="http://runtime-native", api_key="native-key")
    assert isinstance(create_adapter(spec), SynCodeV1RuntimeAdapter)
    with pytest.raises(RegistryError, match="must manage their own user initialization"):
        RuntimeSpec(
            adapter="syncode-v1",
            base_url="http://runtime-native",
            api_key="native-key",
            provision_url="http://provisioner/ensure",
            provision_key="provision-key",
        )


def test_gateway_bootstrap_configuration_uses_generic_runtime_names(monkeypatch, tmp_path):
    monkeypatch.setenv("SYNCODE_RUNTIME_GATEWAY_KEY", "gateway-key")
    monkeypatch.setenv("SYNCODE_RUNTIME_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("SYNCODE_RUNTIME_DEFAULT_NAME", "initial")
    monkeypatch.setenv("SYNCODE_RUNTIME_DEFAULT_ADAPTER", "syncode-v1")
    monkeypatch.setenv("SYNCODE_RUNTIME_DEFAULT_BASE_URL", "http://native-runtime")
    monkeypatch.setenv("SYNCODE_RUNTIME_DEFAULT_API_KEY", "native-key")
    for name in (
        "SYNCODE_HERMES_BASE_URL",
        "SYNCODE_HERMES_API_KEY",
        "SYNCODE_HERMES_PROVISION_URL",
        "SYNCODE_HERMES_PROVISION_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = GatewaySettings.from_env()
    assert settings.default_name == "initial"
    assert settings.default_spec == RuntimeSpec(
        adapter="syncode-v1",
        base_url="http://native-runtime",
        api_key="native-key",
    )


def test_hermes_adapter_translates_generic_workflow_and_hides_skill_prefix():
    body = translate_hermes_run_body(
        json.dumps({"input": "请给我一点提示", "workflow": "progressive-hint", "session_id": "native"}).encode()
    )
    assert json.loads(body) == {
        "input": "/syncode-tutor 请给我一点提示",
        "session_id": "native",
    }
    profile_body = translate_hermes_run_body(
        json.dumps({"input": "refresh", "workflow": "learning-profile"}).encode()
    )
    assert json.loads(profile_body) == {"input": "/syncode-learning-profile refresh"}
    messages = translate_hermes_messages(
        {
            "data": [
                {"role": "user", "content": "/syncode-diagnosis 为什么错了"},
                {"role": "assistant", "content": "先看边界条件"},
            ]
        }
    )
    assert messages["data"][0]["content"] == "为什么错了"
    assert messages["data"][1]["content"] == "先看边界条件"


class FakeStream:
    def __init__(self, lines: list[str]) -> None:
        self.status_code = 200
        self._lines = lines
        self.closed = False

    async def lines(self):
        for line in self._lines:
            yield line

    async def close(self):
        self.closed = True


class FakeRuntime:
    def __init__(self, name: str, healthy: bool = True, list_failure: bool = False) -> None:
        self.name = name
        self.healthy = healthy
        self.list_failure = list_failure
        self.sessions: list[dict] = []
        self.calls: list[tuple] = []
        self.last_session_id: str | None = None
        self.last_run_payload: dict | None = None
        self.run_count = 0

    async def health(self) -> bool:
        self.calls.append(("health",))
        return self.healthy

    async def list_sessions(self, context: RuntimeContext, limit: int) -> RuntimeResponse:
        self.calls.append(("list_sessions", context.user_id, limit))
        if self.list_failure:
            raise RuntimeAdapterError("offline")
        return self._json({"data": self.sessions[:limit]})

    async def create_session(self, context: RuntimeContext, body: bytes) -> RuntimeResponse:
        native_id = f"{self.name}-session-{len(self.sessions) + 1}"
        session = {"id": native_id, "title": json.loads(body).get("title"), "last_active": len(self.sessions) + 1}
        self.sessions.append(session)
        self.calls.append(("create_session", context.user_id, native_id))
        return self._json({"session": session}, 201)

    async def update_session(self, context: RuntimeContext, session_id: str, body: bytes) -> RuntimeResponse:
        self.calls.append(("update_session", session_id, json.loads(body)))
        return self._json({"session": {"id": session_id, **json.loads(body)}})

    async def list_messages(self, context: RuntimeContext, session_id: str, query: str) -> RuntimeResponse:
        self.calls.append(("list_messages", session_id, query))
        return self._json({"data": [{"role": "assistant", "content": "hello", "session_id": session_id}]})

    async def create_run(self, context: RuntimeContext, body: bytes) -> RuntimeResponse:
        payload = json.loads(body)
        self.last_run_payload = payload
        self.run_count += 1
        self.last_session_id = payload.get("session_id")
        self.calls.append(("create_run", self.last_session_id))
        return self._json(
            {"run_id": f"{self.name}-run-{self.run_count}", "session_id": self.last_session_id},
            201,
        )

    async def get_run(self, context: RuntimeContext, run_id: str) -> RuntimeResponse:
        self.calls.append(("get_run", run_id))
        return self._json({"run_id": run_id, "session_id": f"{self.name}-session-1", "status": "completed"})

    async def run_events(
        self,
        context: RuntimeContext,
        run_id: str,
        *,
        last_seq: int | None = None,
        last_event_id: str | None = None,
    ) -> FakeStream:
        self.calls.append(("run_events", run_id, last_seq, last_event_id))
        return FakeStream(
            [
                "id: 3",
                "event: message.delta",
                f'data: {{"run_id":"{run_id}","session_id":"{self.name}-session-1","delta":"ok"}}',
                "",
            ]
        )

    async def control_run(self, context: RuntimeContext, run_id: str, action: str, body: bytes) -> RuntimeResponse:
        self.calls.append(("control_run", run_id, action))
        return self._json({"run_id": run_id, "accepted": True})

    async def list_memories(self, context: RuntimeContext) -> RuntimeResponse:
        self.calls.append(("list_memories", context.user_id))
        return self._json(
            {"data": [{"target": "memory", "label": "MEMORY.md", "entries": [f"{self.name}-fact"]}]}
        )

    async def list_memory_candidates(self, context: RuntimeContext) -> RuntimeResponse:
        self.calls.append(("list_memory_candidates", context.user_id))
        candidate_id = "aaaaaaaa" if self.name == "a" else "bbbbbbbb"
        return self._json({"data": [{"id": candidate_id, "action": "add", "target": "memory"}]})

    async def review_memory_candidate(
        self,
        context: RuntimeContext,
        candidate_id: str,
        action: str,
    ) -> RuntimeResponse:
        self.calls.append(("review_memory_candidate", candidate_id, action))
        status = "approved" if action == "approve" else "rejected"
        return self._json({"candidate_id": candidate_id, "status": status})

    async def list_context_candidates(self, context: RuntimeContext) -> RuntimeResponse:
        self.calls.append(("list_context_candidates", context.user_id))
        candidate_id = "cccccccc" if self.name == "a" else "dddddddd"
        return self._json(
            {
                "data": [
                    {
                        "id": candidate_id,
                        "status": "pending",
                        "summary": f"{self.name} summary",
                        "source_message_ids": ["message-1"],
                        "retained_message_ids": ["message-2"],
                        "token_counts": {"before": 1200, "after": 300},
                    }
                ]
            }
        )

    async def review_context_candidate(
        self,
        context: RuntimeContext,
        candidate_id: str,
        action: str,
        body: bytes,
    ) -> RuntimeResponse:
        payload = json.loads(body)
        self.calls.append(("review_context_candidate", candidate_id, action, payload))
        status = "approved" if action == "approve" else "rejected"
        return self._json({"candidate_id": candidate_id, "status": status})

    @staticmethod
    def _json(payload: dict, status_code: int = 200) -> RuntimeResponse:
        return RuntimeResponse(status_code, json.dumps(payload).encode(), "application/json")


@pytest.fixture
def gateway(monkeypatch, tmp_path):
    runtimes = {
        "http://runtime-a": FakeRuntime("a"),
        "http://runtime-b": FakeRuntime("b"),
        "http://runtime-bad": FakeRuntime("bad", healthy=False),
        "http://runtime-offline": FakeRuntime("offline", list_failure=True),
    }
    monkeypatch.setattr(
        "app.runtime_gateway.server.create_adapter",
        lambda spec: runtimes[spec.base_url],
    )
    settings = GatewaySettings(
        gateway_key="gateway-secret",
        registry_path=tmp_path / "registry.json",
        default_name="runtime-a",
        default_spec=_spec("a"),
    )
    headers = {
        "Authorization": "Bearer gateway-secret",
        "X-SynCode-User-ID": "42",
        "X-SynCode-Session-Key": "syncode-session-key",
    }
    with TestClient(create_app(settings)) as client:
        yield client, headers, runtimes


def test_hot_switch_pins_existing_sessions_runs_events_and_control(gateway):
    client, headers, runtimes = gateway

    old = client.post("/v1/sessions", headers=headers, json={"title": "old"})
    assert old.status_code == 201
    old_session = old.json()["session"]["id"]
    assert decode_public_id(old_session, "session") == ("runtime-a", "a-session-1")

    registration = {
        "adapter": "hermes",
        "base_url": "http://runtime-b",
        "api_key": "key-b",
    }
    assert client.put("/internal/runtimes/runtime-b", headers=headers, json=registration).status_code == 201
    activation = client.post("/internal/runtimes/runtime-b/activate", headers=headers)
    assert activation.status_code == 200
    assert activation.json() == {"active": "runtime-b", "changed": True}

    new = client.post("/v1/sessions", headers=headers, json={"title": "new"})
    new_session = new.json()["session"]["id"]
    assert decode_public_id(new_session, "session") == ("runtime-b", "b-session-1")

    run = client.post("/v1/runs", headers=headers, json={"session_id": old_session, "input": "help"})
    assert run.status_code == 201
    public_run = run.json()["run_id"]
    assert decode_public_id(public_run, "run") == ("runtime-a", "a-run-1")
    assert runtimes["http://runtime-a"].last_session_id == "a-session-1"
    assert runtimes["http://runtime-b"].last_session_id is None

    status_response = client.get(f"/v1/runs/{public_run}", headers=headers)
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    assert decode_public_id(status_response.json()["run_id"], "run") == ("runtime-a", "a-run-1")

    events = client.get(
        f"/v1/runs/{public_run}/events?last_seq=1",
        headers={**headers, "Last-Event-ID": "2"},
    )
    assert events.status_code == 200
    assert "id: 3" in events.text
    assert encode_public_id("run", "runtime-a", "a-run-1") in events.text
    assert encode_public_id("session", "runtime-a", "a-session-1") in events.text
    assert '"run_id":"a-run-1"' not in events.text
    assert ("run_events", "a-run-1", 1, "2") in runtimes["http://runtime-a"].calls

    control = client.post(f"/v1/runs/{public_run}/stop", headers=headers, json={})
    assert control.status_code == 200
    assert ("control_run", "a-run-1", "stop") in runtimes["http://runtime-a"].calls

    listed = client.get("/v1/sessions", headers=headers).json()["data"]
    assert {decode_public_id(row["id"], "session")[0] for row in listed} == {"runtime-a", "runtime-b"}


def test_memory_candidates_are_runtime_pinned_across_hot_switch(gateway):
    client, headers, runtimes = gateway
    registration = {
        "adapter": "hermes",
        "base_url": "http://runtime-b",
        "api_key": "key-b",
    }
    client.put("/internal/runtimes/runtime-b", headers=headers, json=registration)

    before = client.get("/v1/memory-candidates", headers=headers)
    assert before.status_code == 200
    old_candidate = before.json()["data"][0]
    assert decode_public_id(old_candidate["id"], "memory_candidate") == ("runtime-a", "aaaaaaaa")
    assert old_candidate["active"] is True

    client.post("/internal/runtimes/runtime-b/activate", headers=headers)
    after = client.get("/v1/memory-candidates", headers=headers)
    assert after.status_code == 200
    assert {item["runtime"] for item in after.json()["data"]} == {"runtime-a", "runtime-b"}

    approved = client.post(f"/v1/memory-candidates/{old_candidate['id']}/approve", headers=headers)
    assert approved.status_code == 200
    assert decode_public_id(approved.json()["candidate_id"], "memory_candidate") == (
        "runtime-a",
        "aaaaaaaa",
    )
    assert ("review_memory_candidate", "aaaaaaaa", "approve") in runtimes["http://runtime-a"].calls
    assert not any(call[0] == "review_memory_candidate" for call in runtimes["http://runtime-b"].calls)

    memories = client.get("/v1/memories", headers=headers)
    assert memories.status_code == 200
    assert {item["runtime"] for item in memories.json()["data"]} == {"runtime-a", "runtime-b"}


def test_memory_review_rejects_wrong_id_kind_and_unknown_action(gateway):
    client, headers, _ = gateway
    run_id = encode_public_id("run", "runtime-a", "a-run-1")
    assert client.post(f"/v1/memory-candidates/{run_id}/approve", headers=headers).status_code == 400
    candidate_id = encode_public_id("memory_candidate", "runtime-a", "aaaaaaaa")
    assert client.post(f"/v1/memory-candidates/{candidate_id}/erase", headers=headers).status_code == 404


def test_context_candidates_are_runtime_pinned_and_support_edited_approval(gateway):
    client, headers, runtimes = gateway
    client.put(
        "/internal/runtimes/runtime-b",
        headers=headers,
        json={"adapter": "hermes", "base_url": "http://runtime-b", "api_key": "key-b"},
    )

    listed = client.get("/v1/context-candidates", headers=headers)
    assert listed.status_code == 200
    assert {item["runtime"] for item in listed.json()["data"]} == {"runtime-a", "runtime-b"}
    candidate = next(item for item in listed.json()["data"] if item["runtime"] == "runtime-a")
    assert decode_public_id(candidate["id"], "context_candidate") == ("runtime-a", "cccccccc")

    reviewed = client.post(
        f"/v1/context-candidates/{candidate['id']}/approve",
        headers=headers,
        json={"summary": "edited by the user"},
    )
    assert reviewed.status_code == 200
    assert decode_public_id(reviewed.json()["candidate_id"], "context_candidate") == (
        "runtime-a",
        "cccccccc",
    )
    assert (
        "review_context_candidate",
        "cccccccc",
        "approve",
        {"summary": "edited by the user"},
    ) in runtimes["http://runtime-a"].calls
    assert not any(
        call[0] == "review_context_candidate" for call in runtimes["http://runtime-b"].calls
    )


def test_runtime_error_json_still_hides_native_ids(gateway):
    client, headers, runtimes = gateway
    candidate_id = encode_public_id("memory_candidate", "runtime-a", "aaaaaaaa")

    async def fail_review(context, native_id, action):
        assert native_id == "aaaaaaaa"
        return FakeRuntime._json({"candidate_id": native_id, "status": "failed"}, 409)

    runtimes["http://runtime-a"].review_memory_candidate = fail_review
    response = client.post(f"/v1/memory-candidates/{candidate_id}/approve", headers=headers)
    assert response.status_code == 409
    assert response.json()["candidate_id"] == candidate_id
    assert '"candidate_id":"aaaaaaaa"' not in response.text


def test_failed_activation_keeps_current_runtime(gateway):
    client, headers, _ = gateway
    registration = {
        "adapter": "hermes",
        "base_url": "http://runtime-bad",
        "api_key": "key-bad",
    }
    assert client.put("/internal/runtimes/runtime-bad", headers=headers, json=registration).status_code == 201
    response = client.post("/internal/runtimes/runtime-bad/activate", headers=headers)
    assert response.status_code == 503
    assert client.get("/internal/runtimes", headers=headers).json()["active"] == "runtime-a"


def test_inactive_runtime_failure_returns_available_sessions_with_warning(gateway):
    client, headers, _ = gateway
    client.post("/v1/sessions", headers=headers, json={"title": "available"})
    registration = {
        "adapter": "hermes",
        "base_url": "http://runtime-offline",
        "api_key": "key-offline",
    }
    assert client.put("/internal/runtimes/runtime-offline", headers=headers, json=registration).status_code == 201
    response = client.get("/v1/sessions", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["warnings"] == [{"runtime": "runtime-offline", "message": "offline"}]


def test_gateway_requires_trusted_identity_headers(gateway):
    client, headers, _ = gateway
    assert client.get("/v1/sessions").status_code == 401
    invalid = {**headers, "X-SynCode-User-ID": "../42"}
    assert client.get("/v1/sessions", headers=invalid).status_code == 400
    runtimes = client.get("/internal/runtimes", headers=headers).json()["runtimes"]
    assert "api_key" not in runtimes["runtime-a"]
    assert runtimes["runtime-a"]["api_key_configured"] is True


def test_scheduled_learning_profile_refresh_is_user_bound_and_deduplicated(gateway):
    client, headers, runtimes = gateway
    internal_headers = {"Authorization": headers["Authorization"]}
    source = {"user_id": "42", "source_watermark": "10:3:2026-10-09T10:00:00"}

    scheduled = client.post(
        "/internal/learning-profile-refreshes",
        headers=internal_headers,
        json=source,
    )
    assert scheduled.status_code == 202
    assert scheduled.json()["scheduled"] is True
    assert scheduled.json()["runtime"] == "runtime-a"
    assert runtimes["http://runtime-a"].last_run_payload["workflow"] == "learning-profile"
    assert "42" not in runtimes["http://runtime-a"].last_run_payload["input"]

    duplicate = client.post(
        "/internal/learning-profile-refreshes",
        headers=internal_headers,
        json=source,
    )
    assert duplicate.status_code == 200
    assert duplicate.json() == {
        "scheduled": False,
        "reason": "unchanged",
        "source_watermark": source["source_watermark"],
    }
    assert runtimes["http://runtime-a"].run_count == 1


def test_scheduled_learning_profile_refresh_releases_watermark_after_failure(gateway):
    client, headers, runtimes = gateway
    internal_headers = {"Authorization": headers["Authorization"]}
    source = {"user_id": "42", "source_watermark": "11:4:2026-10-09T11:00:00"}
    runtime = runtimes["http://runtime-a"]
    original = runtime.create_run

    async def fail(_context, _body):
        raise RuntimeAdapterError("offline")

    runtime.create_run = fail
    failed = client.post(
        "/internal/learning-profile-refreshes",
        headers=internal_headers,
        json=source,
    )
    assert failed.status_code == 502

    runtime.create_run = original
    retried = client.post(
        "/internal/learning-profile-refreshes",
        headers=internal_headers,
        json=source,
    )
    assert retried.status_code == 202
    assert retried.json()["scheduled"] is True


def test_scheduled_learning_profile_refresh_serializes_newer_watermarks(gateway):
    client, headers, runtimes = gateway
    internal_headers = {"Authorization": headers["Authorization"]}
    first = {"user_id": "42", "source_watermark": "11:4:first"}
    second = {"user_id": "42", "source_watermark": "12:5:second"}
    runtime = runtimes["http://runtime-a"]

    assert client.post(
        "/internal/learning-profile-refreshes", headers=internal_headers, json=first
    ).status_code == 202

    async def still_running(_context, run_id):
        return FakeRuntime._json({"run_id": run_id, "status": "running"})

    runtime.get_run = still_running
    blocked = client.post(
        "/internal/learning-profile-refreshes", headers=internal_headers, json=second
    )
    assert blocked.status_code == 200
    assert blocked.json()["reason"] == "in_progress"
    assert runtime.run_count == 1


def test_scheduled_learning_profile_refresh_rejects_untrusted_or_invalid_identity(gateway):
    client, headers, _ = gateway
    path = "/internal/learning-profile-refreshes"
    assert client.post(path, json={"user_id": "42", "source_watermark": "v1"}).status_code == 401
    assert client.post(
        path,
        headers={"Authorization": headers["Authorization"]},
        json={"user_id": "../42", "source_watermark": "v1"},
    ).status_code == 400


def test_durable_run_events_and_artifacts_survive_gateway_restart(monkeypatch, tmp_path):
    runtime = FakeRuntime("a")
    monkeypatch.setattr("app.runtime_gateway.server.create_adapter", lambda _spec: runtime)
    settings = GatewaySettings(
        gateway_key="gateway-secret",
        registry_path=tmp_path / "registry.json",
        ledger_path=tmp_path / "ledger.sqlite3",
        default_name="runtime-a",
        default_spec=_spec("a"),
    )
    headers = {
        "Authorization": "Bearer gateway-secret",
        "X-SynCode-User-ID": "42",
        "X-SynCode-Session-Key": "syncode-session-key",
    }

    async def terminal_events(context, run_id, *, last_seq=None, last_event_id=None):
        return FakeStream(
            [
                "id: 4",
                "event: run.completed",
                f'data: {{"run_id":"{run_id}","status":"completed","output":"review result"}}',
                "",
            ]
        )

    runtime.run_events = terminal_events
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/v1/runs",
            headers=headers,
            json={"input": "review", "workflow": "error-diagnosis"},
        )
        assert created.status_code == 201
        run_id = created.json()["run_id"]
        assert "event: run.completed" in client.get(f"/v1/runs/{run_id}/events", headers=headers).text
        assert client.get(f"/v1/runs/{run_id}/artifacts", headers=headers).json()["data"][0][
            "artifact_type"
        ] == "diagnosis_report"

    upstream_calls: list[str] = []

    async def unavailable_get(context, run_id):
        upstream_calls.append("get")
        raise RuntimeAdapterError("offline")

    async def unavailable_events(context, run_id, *, last_seq=None, last_event_id=None):
        upstream_calls.append("events")
        raise RuntimeAdapterError("offline")

    runtime.get_run = unavailable_get
    runtime.run_events = unavailable_events
    with TestClient(create_app(settings)) as client:
        stored = client.get(f"/v1/runs/{run_id}", headers=headers)
        assert stored.status_code == 200
        assert stored.json()["status"] == "completed"
        assert stored.json()["runtime"] == "runtime-a"
        assert stored.json()["runtime_available"] is False

        replay = client.get(f"/v1/runs/{run_id}/events", headers=headers)
        assert replay.status_code == 200
        assert "review result" in replay.text
        after_terminal = client.get(f"/v1/runs/{run_id}/events?last_seq=4", headers=headers)
        assert after_terminal.status_code == 200
        assert after_terminal.text == ""
        assert upstream_calls == ["get"]

        artifacts = client.get(f"/v1/runs/{run_id}/artifacts", headers=headers).json()["data"]
        assert artifacts[0]["summary"] == "review result"


def test_durable_run_resources_reject_cross_user_access(gateway):
    client, headers, _ = gateway
    created = client.post("/v1/runs", headers=headers, json={"input": "help"})
    run_id = created.json()["run_id"]
    other_user = {**headers, "X-SynCode-User-ID": "43"}

    assert client.get(f"/v1/runs/{run_id}", headers=other_user).status_code == 404
    assert client.get(f"/v1/runs/{run_id}/events", headers=other_user).status_code == 404
    assert client.get(f"/v1/runs/{run_id}/artifacts", headers=other_user).status_code == 404
    assert client.post(f"/v1/runs/{run_id}/stop", headers=other_user, json={}).status_code == 404


def test_concurrency_admission_limits_user_and_runtime(monkeypatch, tmp_path):
    runtime = FakeRuntime("a")
    monkeypatch.setattr("app.runtime_gateway.server.create_adapter", lambda _spec: runtime)
    headers = {
        "Authorization": "Bearer gateway-secret",
        "X-SynCode-User-ID": "42",
        "X-SynCode-Session-Key": "syncode-session-key",
    }

    per_user = GatewaySettings(
        gateway_key="gateway-secret",
        registry_path=tmp_path / "user-registry.json",
        ledger_path=tmp_path / "user-ledger.sqlite3",
        default_name="runtime-a",
        default_spec=_spec("a"),
        max_concurrent_runs_per_user=1,
        max_concurrent_runs_per_runtime=10,
    )
    with TestClient(create_app(per_user)) as client:
        assert client.post("/v1/runs", headers=headers, json={"input": "first"}).status_code == 201
        limited = client.post("/v1/runs", headers=headers, json={"input": "second"})
        assert limited.status_code == 429
        assert limited.json()["detail"]["scope"] == "this user"

    per_runtime = GatewaySettings(
        gateway_key="gateway-secret",
        registry_path=tmp_path / "runtime-registry.json",
        ledger_path=tmp_path / "runtime-ledger.sqlite3",
        default_name="runtime-a",
        default_spec=_spec("a"),
        max_concurrent_runs_per_user=2,
        max_concurrent_runs_per_runtime=1,
    )
    with TestClient(create_app(per_runtime)) as client:
        assert client.post("/v1/runs", headers=headers, json={"input": "first"}).status_code == 201
        other_user = {**headers, "X-SynCode-User-ID": "43"}
        limited = client.post("/v1/runs", headers=other_user, json={"input": "second"})
        assert limited.status_code == 429
        assert limited.json()["detail"]["scope"] == "Runtime runtime-a"


def test_new_resources_fail_over_but_pinned_sessions_do_not(monkeypatch, tmp_path):
    runtime_a = FakeRuntime("a")
    runtime_b = FakeRuntime("b")
    runtimes = {"http://runtime-a": runtime_a, "http://runtime-b": runtime_b}
    monkeypatch.setattr("app.runtime_gateway.server.create_adapter", lambda spec: runtimes[spec.base_url])
    settings = GatewaySettings(
        gateway_key="gateway-secret",
        registry_path=tmp_path / "registry.json",
        ledger_path=tmp_path / "ledger.sqlite3",
        default_name="runtime-a",
        default_spec=_spec("a"),
    )
    headers = {
        "Authorization": "Bearer gateway-secret",
        "X-SynCode-User-ID": "42",
        "X-SynCode-Session-Key": "syncode-session-key",
    }

    with TestClient(create_app(settings)) as client:
        client.put(
            "/internal/runtimes/runtime-b",
            headers=headers,
            json={"adapter": "hermes", "base_url": "http://runtime-b", "api_key": "key-b"},
        )
        pinned_session = client.post("/v1/sessions", headers=headers, json={"title": "pinned"}).json()[
            "session"
        ]["id"]

        async def fail_create_run(context, body):
            raise RuntimeAdapterError("runtime-a is offline")

        async def fail_create_session(context, body):
            raise RuntimeAdapterError("runtime-a is offline")

        runtime_a.create_run = fail_create_run
        runtime_a.create_session = fail_create_session

        pinned = client.post(
            "/v1/runs",
            headers=headers,
            json={"session_id": pinned_session, "input": "must stay pinned"},
        )
        assert pinned.status_code == 502
        assert runtime_b.run_count == 0

        sessionless = client.post("/v1/runs", headers=headers, json={"input": "may fail over"})
        assert sessionless.status_code == 201
        assert sessionless.json()["runtime"] == "runtime-b"
        assert sessionless.json()["degraded_from"] == "runtime-a"

        new_session = client.post("/v1/sessions", headers=headers, json={"title": "may fail over"})
        assert new_session.status_code == 201
        assert new_session.json()["runtime"] == "runtime-b"
        assert new_session.json()["degraded_from"] == "runtime-a"


def test_sse_rewrite_preserves_event_and_rewrites_nested_ids():
    frame = _rewrite_sse_frame(
        [
            "event: approval.request",
            'data: {"run_id":"run-1","details":{"session_id":"session-1"},'
            '"context_candidate_id":"cafebabe"}',
        ],
        "hermes",
    )
    assert frame.startswith("event: approval.request\ndata: ")
    payload = json.loads(frame.split("data: ", 1)[1])
    assert decode_public_id(payload["run_id"], "run") == ("hermes", "run-1")
    assert decode_public_id(payload["details"]["session_id"], "session") == ("hermes", "session-1")
    assert decode_public_id(payload["context_candidate_id"], "context_candidate") == (
        "hermes",
        "cafebabe",
    )
