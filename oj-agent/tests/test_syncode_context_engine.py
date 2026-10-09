from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


class _SessionDB:
    def __init__(self, watermark: int) -> None:
        self.watermark = watermark

    def get_active_message_watermark(self, _session_id: str) -> int:
        return self.watermark


def _load_context_engine(monkeypatch, tmp_path, state: dict):
    agent_module = ModuleType("agent")
    compressor_module = ModuleType("agent.context_compressor")
    metadata_module = ModuleType("agent.model_metadata")
    redact_module = ModuleType("agent.redact")
    constants_module = ModuleType("hermes_constants")
    tools_module = ModuleType("tools")
    approval_module = ModuleType("tools.approval")
    approval_context_module = ModuleType("tools.approval_context")
    approval_wait_module = ModuleType("tools.approval_gateway_wait")

    class ContextCompressor:
        def __init__(self, **_kwargs) -> None:
            self._previous_summary = "prior summary"
            self._last_summary_error = None
            self._last_compress_aborted = False
            self._summary_failure_cooldown_until = 0.0
            self._consecutive_timeout_failures = 0
            self._consecutive_truncation_failures = 0
            self._cooldown_persist_failed = False
            self._summary_model_fallen_back = True
            self._last_summary_auth_failure = True
            self._last_summary_network_failure = True
            self._last_summary_truncated_failure = True
            self._last_summary_empty_content_failure = True
            self._consecutive_overload_aborts = 3
            self.durable_calls = []
            self._session_db = None
            self._session_id = ""

        def compress(self, messages, *_args, **_kwargs):
            return messages

        def _generate_summary(self, _turns, **_kwargs):
            self._previous_summary = "generated summary"
            self._summary_failure_cooldown_until = 0.0
            self._consecutive_timeout_failures = 0
            self._consecutive_truncation_failures = 0
            self._cooldown_persist_failed = False
            self._summary_model_fallen_back = False
            self._last_summary_auth_failure = False
            self._last_summary_network_failure = False
            self._last_summary_truncated_failure = False
            self._last_summary_empty_content_failure = False
            self._consecutive_overload_aborts = 0
            return self._with_summary_prefix("generated summary")

        def _durable_write(self, *args):
            self.durable_calls.append(args)
            return True

        def _persist_consecutive_overload_aborts(self):
            self.durable_calls.append(("persist_overload", self._consecutive_overload_aborts))

        @staticmethod
        def _strip_summary_prefix(summary: str) -> str:
            return summary.removeprefix("[summary]\n")

        @classmethod
        def _with_summary_prefix(cls, summary: str) -> str:
            return f"[summary]\n{cls._strip_summary_prefix(summary)}"

    compressor_module.ContextCompressor = ContextCompressor
    metadata_module.estimate_messages_tokens_rough = lambda messages: sum(
        len(str(message.get("content") or "")) for message in messages
    ) // 4
    redact_module.redact_sensitive_text = lambda value, **_kwargs: value.replace("secret", "[redacted]")
    constants_module.get_hermes_home = lambda: str(tmp_path / "hermes")
    approval_module._gateway_notify_cb = lambda _run_id: state.get("notify")
    approval_module.resolve_gateway_approval = lambda *_args, **_kwargs: state.get("resolve_count", 1)
    approval_context_module.get_current_session_key = lambda _default="": state.get("run_id", "run-1")

    def await_decision(_run_id, _notify, approval_data, **_kwargs):
        state["approval_data"] = approval_data
        return state["await"](approval_data)

    approval_wait_module._await_gateway_decision = await_decision
    for name, module in {
        "agent": agent_module,
        "agent.context_compressor": compressor_module,
        "agent.model_metadata": metadata_module,
        "agent.redact": redact_module,
        "hermes_constants": constants_module,
        "tools": tools_module,
        "tools.approval": approval_module,
        "tools.approval_context": approval_context_module,
        "tools.approval_gateway_wait": approval_wait_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    root = Path(__file__).resolve().parents[2]
    module_path = root / "hermes" / "context_engine" / "syncode_reviewed" / "__init__.py"
    spec = importlib.util.spec_from_file_location("test_syncode_reviewed_context_engine", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_context_engine_commits_only_the_user_reviewed_summary(monkeypatch, tmp_path):
    state = {"notify": lambda _data: None, "run_id": "run-1"}
    module = _load_context_engine(monkeypatch, tmp_path, state)

    def approve(_approval_data):
        candidate = module.list_context_candidates()[0]
        candidate.update(status="approved", edited_summary="learner edited summary")
        module._write_candidate(candidate)
        return {"resolved": True, "choice": "once"}

    state["await"] = approve
    engine = module.SynCodeReviewedContextEngine()
    engine._session_id = "session-1"
    engine._session_db = _SessionDB(10)
    turns = [
        {"id": "m1", "role": "user", "content": "secret question"},
        {"id": "m2", "role": "assistant", "content": "first answer"},
    ]
    engine._review_all_messages = [*turns, {"id": "m3", "role": "user", "content": "latest"}]

    summary = engine._generate_summary(turns)

    assert summary == "[summary]\nlearner edited summary"
    candidate = module.list_context_candidates()[0]
    assert candidate["status"] == "approved"
    assert candidate["source_message_ids"] == ["m1", "m2"]
    assert candidate["retained_message_ids"] == ["m3"]
    assert candidate["source_messages"][0]["content"] == "[redacted] question"
    assert state["approval_data"]["review_kind"] == "context_summary"
    assert state["approval_data"]["context_candidate_id"] == candidate["id"]


def test_context_engine_rejects_approval_when_session_watermark_changed(monkeypatch, tmp_path):
    state = {"notify": lambda _data: None, "run_id": "run-1"}
    module = _load_context_engine(monkeypatch, tmp_path, state)
    database = _SessionDB(20)

    def approve_after_new_message(_approval_data):
        candidate = module.list_context_candidates()[0]
        candidate.update(status="approved")
        module._write_candidate(candidate)
        database.watermark = 21
        return {"resolved": True, "choice": "once"}

    state["await"] = approve_after_new_message
    engine = module.SynCodeReviewedContextEngine()
    engine._session_id = "session-1"
    engine._session_db = database
    turns = [{"id": "m1", "role": "user", "content": "question"}]
    engine._review_all_messages = list(turns)

    assert engine._generate_summary(turns) is None
    assert engine._previous_summary == "prior summary"
    assert engine._last_compress_aborted is True
    assert engine._summary_model_fallen_back is True
    assert engine._last_summary_auth_failure is True
    assert engine._last_summary_network_failure is True
    assert engine._last_summary_truncated_failure is True
    assert engine._last_summary_empty_content_failure is True
    assert engine._consecutive_overload_aborts == 3
    assert ("persist_overload", 3) in engine.durable_calls
    assert module.list_context_candidates()[0]["status"] == "stale"


def test_context_candidate_review_lifecycle_is_atomic_and_fail_closed(monkeypatch, tmp_path):
    state = {
        "notify": lambda _data: None,
        "run_id": "run-1",
        "await": lambda _data: {"resolved": False, "choice": None},
        "resolve_count": 1,
    }
    module = _load_context_engine(monkeypatch, tmp_path, state)
    candidate = {
        "id": "deadbeef",
        "status": "pending",
        "run_id": "run-1",
        "approval_request_id": "context-deadbeef",
        "summary": "generated",
    }
    module._write_candidate(candidate)

    approved = module.review_context_candidate("deadbeef", "approve", "edited")
    assert approved["status"] == "approved"
    assert approved["edited_summary"] == "edited"
    assert (tmp_path / "hermes" / "pending" / "context" / "deadbeef.json").stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError, match="already been reviewed"):
        module.review_context_candidate("deadbeef", "reject")

    state["resolve_count"] = 0
    module._write_candidate(
        {
            "id": "cafebabe",
            "status": "pending",
            "run_id": "run-2",
            "approval_request_id": "context-cafebabe",
            "summary": "generated",
        }
    )
    with pytest.raises(ValueError, match="no longer waiting"):
        module.review_context_candidate("cafebabe", "reject")
    assert module.get_context_candidate("cafebabe")["status"] == "stale"
