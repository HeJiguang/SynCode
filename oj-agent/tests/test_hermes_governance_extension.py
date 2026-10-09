from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace


def _load_extension(monkeypatch, state: dict):
    aiohttp_module = ModuleType("aiohttp")

    def json_response(payload, status=200):
        return SimpleNamespace(
            status=status,
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )

    aiohttp_module.web = SimpleNamespace(json_response=json_response)
    tools_module = ModuleType("tools")
    memory_module = ModuleType("tools.memory_tool")
    approval_module = ModuleType("tools.write_approval")
    plugins_module = ModuleType("plugins")
    context_engine_module = ModuleType("plugins.context_engine")
    context_module = ModuleType("plugins.context_engine.syncode_reviewed")

    class Store:
        memory_entries = ["prefers progressive hints"]
        user_entries = ["learning Java"]
        memory_char_limit = 2200
        user_char_limit = 1375

    memory_module.load_on_disk_store = lambda: Store()
    memory_module.apply_memory_pending = lambda payload, _store: state["apply"](payload)
    approval_module.MEMORY = "memory"
    approval_module.list_pending = lambda _subsystem: list(state["pending"].values())
    approval_module.get_pending = lambda _subsystem, candidate_id: state["pending"].get(candidate_id)

    def discard(_subsystem, candidate_id):
        state["discarded"].append(candidate_id)
        return state["pending"].pop(candidate_id, None) is not None

    approval_module.discard_pending = discard
    context_module.list_context_candidates = lambda: list(state.get("contexts", {}).values())
    context_module.get_context_candidate = lambda candidate_id: state.get("contexts", {}).get(candidate_id)

    def review_context(candidate_id, action, edited_summary=None):
        candidate = state.get("contexts", {}).get(candidate_id)
        if candidate is None:
            raise KeyError(candidate_id)
        if candidate.get("status") != "pending":
            raise ValueError("Context candidate has already been reviewed.")
        candidate.update(
            status="approved" if action == "approve" else "rejected",
            edited_summary=edited_summary if action == "approve" else None,
        )
        return candidate

    context_module.review_context_candidate = review_context
    tools_module.memory_tool = memory_module
    tools_module.write_approval = approval_module
    monkeypatch.setitem(sys.modules, "tools", tools_module)
    monkeypatch.setitem(sys.modules, "tools.memory_tool", memory_module)
    monkeypatch.setitem(sys.modules, "tools.write_approval", approval_module)
    monkeypatch.setitem(sys.modules, "plugins", plugins_module)
    monkeypatch.setitem(sys.modules, "plugins.context_engine", context_engine_module)
    monkeypatch.setitem(sys.modules, "plugins.context_engine.syncode_reviewed", context_module)
    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp_module)

    root = Path(__file__).resolve().parents[2]
    module_path = root / "hermes" / "extensions" / "api_server_syncode_governance.py"
    spec = importlib.util.spec_from_file_location("test_syncode_governance", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Adapter:
    @staticmethod
    def _check_auth(_request):
        return None


def _payload(response) -> dict:
    return json.loads(response.body)


def test_governance_extension_lists_native_memory_and_pending(monkeypatch):
    state = {
        "pending": {
            "abcd1234": {
                "id": "abcd1234",
                "action": "add",
                "summary": "add preference",
                "origin": "foreground",
                "created_at": 1.0,
                "payload": {"action": "add", "target": "memory", "content": "prefers examples"},
            },
            "../../bad": {"id": "../../bad", "payload": {"action": "add"}},
        },
        "discarded": [],
        "apply": lambda _payload: {"success": True},
    }
    module = _load_extension(monkeypatch, state)
    request = SimpleNamespace(match_info={})

    memories = _payload(asyncio.run(module._handle_memories(_Adapter(), request)))
    assert memories["data"][0]["entries"] == ["prefers progressive hints"]
    assert memories["data"][1]["entries"] == ["learning Java"]
    candidates = _payload(asyncio.run(module._handle_memory_candidates(_Adapter(), request)))
    assert [item["id"] for item in candidates["data"]] == ["abcd1234"]
    assert candidates["data"][0]["proposal"]["content"] == "prefers examples"


def test_governance_extension_approves_rejects_and_rejects_traversal(monkeypatch):
    state = {
        "pending": {
            "abcd1234": {
                "id": "abcd1234",
                "payload": {"action": "add", "target": "memory", "content": "fact"},
            },
            "deadbeef": {
                "id": "deadbeef",
                "payload": {"action": "add", "target": "user", "content": "profile fact"},
            },
        },
        "discarded": [],
        "apply": lambda payload: {"success": payload["target"] == "memory"},
    }
    module = _load_extension(monkeypatch, state)

    approved = asyncio.run(
        module._handle_approve_memory_candidate(
            _Adapter(), SimpleNamespace(match_info={"candidate_id": "abcd1234"})
        )
    )
    assert approved.status == 200
    assert _payload(approved)["status"] == "approved"
    assert state["discarded"] == ["abcd1234"]

    failed = asyncio.run(
        module._handle_approve_memory_candidate(
            _Adapter(), SimpleNamespace(match_info={"candidate_id": "deadbeef"})
        )
    )
    assert failed.status == 409
    assert "deadbeef" in state["pending"]
    assert state["discarded"] == ["abcd1234"]

    traversal = asyncio.run(
        module._handle_reject_memory_candidate(
            _Adapter(), SimpleNamespace(match_info={"candidate_id": "../bad"})
        )
    )
    assert traversal.status == 400
    assert state["discarded"] == ["abcd1234"]

    rejected = asyncio.run(
        module._handle_reject_memory_candidate(
            _Adapter(), SimpleNamespace(match_info={"candidate_id": "deadbeef"})
        )
    )
    assert rejected.status == 200
    assert _payload(rejected)["status"] == "rejected"
    assert state["discarded"] == ["abcd1234", "deadbeef"]


class _JsonRequest:
    def __init__(self, candidate_id: str, payload: dict | None = None) -> None:
        self.match_info = {"candidate_id": candidate_id}
        self.can_read_body = payload is not None
        self._payload = payload or {}

    async def json(self):
        return self._payload


def test_governance_extension_lists_and_reviews_context_candidates(monkeypatch):
    state = {
        "pending": {},
        "discarded": [],
        "apply": lambda _payload: {"success": True},
        "contexts": {
            "cafebabe": {
                "id": "cafebabe",
                "status": "pending",
                "summary": "generated summary",
                "source_tokens": 900,
                "retained_tokens": 300,
                "summary_tokens": 100,
            }
        },
    }
    module = _load_extension(monkeypatch, state)

    listed = _payload(asyncio.run(module._handle_context_candidates(_Adapter(), _JsonRequest(""))))
    assert listed["total"] == 1
    assert listed["data"][0]["summary"] == "generated summary"

    approved = asyncio.run(
        module._handle_approve_context_candidate(
            _Adapter(), _JsonRequest("cafebabe", {"summary": "learner edited summary"})
        )
    )
    assert approved.status == 200
    assert state["contexts"]["cafebabe"]["edited_summary"] == "learner edited summary"

    repeated = asyncio.run(
        module._handle_reject_context_candidate(_Adapter(), _JsonRequest("cafebabe"))
    )
    assert repeated.status == 409

    malformed = asyncio.run(
        module._handle_reject_context_candidate(_Adapter(), _JsonRequest("../bad"))
    )
    assert malformed.status == 400
