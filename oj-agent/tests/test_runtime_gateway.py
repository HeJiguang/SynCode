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
        self.last_session_id = payload.get("session_id")
        self.calls.append(("create_run", self.last_session_id))
        return self._json({"run_id": f"{self.name}-run-1", "session_id": self.last_session_id}, 201)

    async def run_events(self, context: RuntimeContext, run_id: str) -> FakeStream:
        self.calls.append(("run_events", run_id))
        return FakeStream(
            [
                "event: message.delta",
                f'data: {{"run_id":"{run_id}","session_id":"{self.name}-session-1","delta":"ok"}}',
                "",
            ]
        )

    async def control_run(self, context: RuntimeContext, run_id: str, action: str, body: bytes) -> RuntimeResponse:
        self.calls.append(("control_run", run_id, action))
        return self._json({"run_id": run_id, "accepted": True})

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

    events = client.get(f"/v1/runs/{public_run}/events", headers=headers)
    assert events.status_code == 200
    assert encode_public_id("run", "runtime-a", "a-run-1") in events.text
    assert encode_public_id("session", "runtime-a", "a-session-1") in events.text
    assert '"run_id":"a-run-1"' not in events.text

    control = client.post(f"/v1/runs/{public_run}/stop", headers=headers, json={})
    assert control.status_code == 200
    assert ("control_run", "a-run-1", "stop") in runtimes["http://runtime-a"].calls

    listed = client.get("/v1/sessions", headers=headers).json()["data"]
    assert {decode_public_id(row["id"], "session")[0] for row in listed} == {"runtime-a", "runtime-b"}


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


def test_sse_rewrite_preserves_event_and_rewrites_nested_ids():
    frame = _rewrite_sse_frame(
        ["event: tool.started", 'data: {"run_id":"run-1","details":{"session_id":"session-1"}}'],
        "hermes",
    )
    assert frame.startswith("event: tool.started\ndata: ")
    payload = json.loads(frame.split("data: ", 1)[1])
    assert decode_public_id(payload["run_id"], "run") == ("hermes", "run-1")
    assert decode_public_id(payload["details"]["session_id"], "session") == ("hermes", "session-1")
