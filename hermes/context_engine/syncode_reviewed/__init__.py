"""Hermes-native context compressor with a user review gate."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any
from uuid import uuid4

from agent.context_compressor import ContextCompressor
from agent.model_metadata import estimate_messages_tokens_rough
from agent.redact import redact_sensitive_text
from hermes_constants import get_hermes_home
from tools.approval import _gateway_notify_cb
from tools.approval_context import get_current_session_key
from tools.approval_gateway_wait import _await_gateway_decision


_CANDIDATE_ID_RE = re.compile(r"^[0-9a-f]{8}$")
_MAX_EDIT_CHARS = 20_000
_MAX_SOURCE_MESSAGES = 80
_MAX_SOURCE_CONTENT_CHARS = 4_000
_MISSING = object()
_SUMMARY_STATE_FIELDS = (
    "_previous_summary",
    "_summary_failure_cooldown_until",
    "_consecutive_timeout_failures",
    "_consecutive_truncation_failures",
    "_cooldown_persist_failed",
    "_summary_model_fallen_back",
    "_last_summary_auth_failure",
    "_last_summary_network_failure",
    "_last_summary_truncated_failure",
    "_last_summary_empty_content_failure",
    "_consecutive_overload_aborts",
)


class SynCodeReviewedContextEngine(ContextCompressor):
    """Generate summaries with Hermes, then require an explicit review before commit."""

    def __init__(self) -> None:
        super().__init__(
            model="",
            threshold_percent=0.75,
            protect_first_n=3,
            protect_last_n=6,
            summary_target_ratio=0.20,
            abort_on_summary_failure=True,
            tail_mode="lean",
        )
        self._review_all_messages: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "syncode_reviewed"

    def clone_for_agent(self) -> "SynCodeReviewedContextEngine":
        return type(self)()

    def compress(self, messages: list[dict[str, Any]], *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        self._review_all_messages = list(messages)
        try:
            return super().compress(messages, *args, **kwargs)
        finally:
            self._review_all_messages = []

    def _generate_summary(
        self,
        turns_to_summarize: list[dict[str, Any]],
        focus_topic: str | None = None,
        memory_context: str = "",
        bypass_cooldown: bool = False,
    ) -> str | None:
        previous_state = self._capture_summary_state()
        summary = super()._generate_summary(
            turns_to_summarize,
            focus_topic=focus_topic,
            memory_context=memory_context,
            bypass_cooldown=bypass_cooldown,
        )
        if not summary:
            return None

        run_id = get_current_session_key("")
        notify = _gateway_notify_cb(run_id) if run_id else None
        if not run_id or notify is None:
            self._reject_generated_summary(previous_state, "No interactive context-review bridge is available.")
            return None

        candidate_id = uuid4().hex[:8]
        request_id = f"context-{candidate_id}"
        source_version = self._source_version(turns_to_summarize)
        watermark = self._message_watermark()
        candidate = {
            "id": candidate_id,
            "status": "pending",
            "session_id": self._session_id,
            "run_id": run_id,
            "approval_request_id": request_id,
            "source_version": source_version,
            "source_watermark": watermark,
            "source_message_ids": self._message_ids(turns_to_summarize),
            "retained_message_ids": self._retained_message_ids(turns_to_summarize),
            "source_tokens": estimate_messages_tokens_rough(turns_to_summarize),
            "retained_tokens": estimate_messages_tokens_rough(
                [message for message in self._review_all_messages if message not in turns_to_summarize]
            ),
            "summary_tokens": estimate_messages_tokens_rough(
                [{"role": "user", "content": self._strip_summary_prefix(summary)}]
            ),
            "summary": self._strip_summary_prefix(summary),
            "edited_summary": None,
            "source_messages": self._source_messages(turns_to_summarize),
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        _write_candidate(candidate)
        decision = _await_gateway_decision(
            run_id,
            notify,
            {
                "request_id": request_id,
                "command": f"Review context summary {candidate_id}",
                "description": "Context compression summary requires user review before commit.",
                "pattern_key": f"syncode_context_review:{candidate_id}",
                "pattern_keys": [f"syncode_context_review:{candidate_id}"],
                "review_kind": "context_summary",
                "context_candidate_id": candidate_id,
                "allow_session": False,
                "allow_permanent": False,
            },
            surface="syncode_context_review",
        )
        refreshed = get_context_candidate(candidate_id)
        approved = bool(decision.get("resolved") and decision.get("choice") == "once")
        if not approved or refreshed is None or refreshed.get("status") != "approved":
            self._reject_generated_summary(previous_state, "The context summary was rejected or expired.")
            if refreshed is not None and refreshed.get("status") == "pending":
                refreshed.update(status="rejected", updated_at=time.time())
                _write_candidate(refreshed)
            return None
        if refreshed.get("source_version") != source_version or refreshed.get("source_watermark") != self._message_watermark():
            refreshed.update(status="stale", updated_at=time.time())
            _write_candidate(refreshed)
            self._reject_generated_summary(previous_state, "The context changed while the summary was under review.")
            return None
        reviewed_summary = refreshed.get("edited_summary") or refreshed.get("summary")
        if not isinstance(reviewed_summary, str) or not reviewed_summary.strip():
            self._reject_generated_summary(previous_state, "The approved context summary is empty.")
            return None
        normalized = self._with_summary_prefix(reviewed_summary[:_MAX_EDIT_CHARS])
        self._previous_summary = self._strip_summary_prefix(normalized)
        return normalized

    def _capture_summary_state(self) -> dict[str, Any]:
        state = {name: getattr(self, name, _MISSING) for name in _SUMMARY_STATE_FIELDS}
        state["_last_summary_error"] = getattr(self, "_last_summary_error", _MISSING)
        return state

    def _reject_generated_summary(self, previous_state: dict[str, Any], reason: str) -> None:
        for name in _SUMMARY_STATE_FIELDS:
            value = previous_state.get(name, _MISSING)
            if value is not _MISSING:
                setattr(self, name, value)

        # Hermes publishes successful summary bookkeeping before this review gate runs. Restore the
        # corresponding durable counters too, so a rejection is a true pre-commit no-op.
        durable_write = getattr(self, "_durable_write", None)
        if callable(durable_write):
            try:
                cooldown_until = previous_state.get("_summary_failure_cooldown_until", 0.0)
                previous_error = previous_state.get("_last_summary_error")
                if isinstance(cooldown_until, (int, float)) and cooldown_until > time.monotonic():
                    durable_write(
                        "record_compression_failure_cooldown",
                        "compression failure cooldown review rollback",
                        time.time() + (cooldown_until - time.monotonic()),
                        previous_error if isinstance(previous_error, str) else None,
                    )
                else:
                    durable_write(
                        "clear_compression_failure_cooldown",
                        "compression failure cooldown review rollback",
                    )
            except Exception:
                pass

        persist_overload = getattr(self, "_persist_consecutive_overload_aborts", None)
        if (
            previous_state.get("_consecutive_overload_aborts", _MISSING) is not _MISSING
            and callable(persist_overload)
        ):
            try:
                persist_overload()
            except Exception:
                pass

        self._last_summary_error = reason
        self._last_compress_aborted = True

    def _message_watermark(self) -> int | None:
        getter = getattr(self._session_db, "get_active_message_watermark", None)
        if not callable(getter) or not self._session_id:
            return None
        try:
            return int(getter(self._session_id))
        except Exception:
            return None

    @staticmethod
    def _message_ids(messages: list[dict[str, Any]]) -> list[str]:
        return [_message_id(message, index) for index, message in enumerate(messages)]

    def _retained_message_ids(self, source: list[dict[str, Any]]) -> list[str]:
        source_objects = {id(message) for message in source}
        return [
            _message_id(message, index)
            for index, message in enumerate(self._review_all_messages)
            if id(message) not in source_objects
        ]

    @staticmethod
    def _source_version(messages: list[dict[str, Any]]) -> str:
        serialized = json.dumps(messages, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _source_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
        visible: list[dict[str, str]] = []
        for index, message in enumerate(messages[:_MAX_SOURCE_MESSAGES]):
            content = message.get("content", "")
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False, default=str)
            content = redact_sensitive_text(content, force=True, redact_url_credentials=True)
            visible.append(
                {
                    "id": _message_id(message, index),
                    "role": str(message.get("role") or "unknown"),
                    "content": content[:_MAX_SOURCE_CONTENT_CHARS],
                }
            )
        return visible


def register(context: Any) -> None:
    context.register_context_engine(SynCodeReviewedContextEngine())


def list_context_candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    directory = _candidate_dir()
    if not directory.exists():
        return rows
    for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        if not _CANDIDATE_ID_RE.fullmatch(path.stem):
            continue
        candidate = _read_candidate(path)
        if candidate is not None:
            rows.append(candidate)
    return rows[:100]


def get_context_candidate(candidate_id: str) -> dict[str, Any] | None:
    if not _CANDIDATE_ID_RE.fullmatch(candidate_id):
        return None
    return _read_candidate(_candidate_dir() / f"{candidate_id}.json")


def review_context_candidate(candidate_id: str, action: str, edited_summary: str | None = None) -> dict[str, Any]:
    candidate = get_context_candidate(candidate_id)
    if candidate is None:
        raise KeyError(candidate_id)
    if candidate.get("status") != "pending":
        raise ValueError("Context candidate has already been reviewed.")
    if action not in {"approve", "reject"}:
        raise ValueError("Unsupported context review action.")
    if edited_summary is not None:
        edited_summary = edited_summary.strip()
        if not edited_summary:
            raise ValueError("Edited summary must not be empty.")
        if len(edited_summary) > _MAX_EDIT_CHARS:
            raise ValueError(f"Edited summary exceeds {_MAX_EDIT_CHARS} characters.")
    candidate.update(
        status="approved" if action == "approve" else "rejected",
        edited_summary=edited_summary if action == "approve" else None,
        updated_at=time.time(),
    )
    _write_candidate(candidate)
    from tools.approval import resolve_gateway_approval

    choice = "once" if action == "approve" else "deny"
    resolved = resolve_gateway_approval(
        str(candidate.get("run_id") or ""),
        choice,
        request_id=str(candidate.get("approval_request_id") or ""),
    )
    if resolved != 1:
        candidate.update(status="stale", updated_at=time.time())
        _write_candidate(candidate)
        raise ValueError("The owning Run is no longer waiting for this context review.")
    return candidate


def _candidate_dir() -> Path:
    return Path(get_hermes_home()) / "pending" / "context"


def _read_candidate(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _write_candidate(candidate: dict[str, Any]) -> None:
    candidate_id = str(candidate.get("id") or "")
    if not _CANDIDATE_ID_RE.fullmatch(candidate_id):
        raise ValueError("Invalid context candidate ID.")
    directory = _candidate_dir()
    directory.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{candidate_id}.", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(candidate, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, directory / f"{candidate_id}.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _message_id(message: dict[str, Any], index: int) -> str:
    for key in ("_row_id", "id", "message_id"):
        value = message.get(key)
        if value is not None:
            return str(value)
    digest = hashlib.sha256(
        json.dumps(message, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    return f"message-{index}-{digest}"
