from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
from threading import Lock, RLock
from typing import Any

from app.conversations.repository import ConversationRepository
from app.core.config import load_settings
from app.domain.conversations import (
    Conversation,
    ConversationMessage,
    ConversationSnapshot,
    ConversationStatus,
    MemoryItem,
    MessageRole,
    MessageStatus,
)
from app.domain.tool_permissions import (
    ToolActionRequest,
    ToolApproval,
    ToolApprovalStatus,
    ToolPolicyDecision,
    ToolPolicyResult,
    ToolRiskLevel,
    evaluate_tool_request,
    normalize_public_github_repository,
)
from app.integrations.github_repository import (
    GitHubRepositoryError,
    download_github_snapshot,
    prepare_github_snapshot_request,
)


class ConversationLimitReached(RuntimeError):
    pass


class ConversationBusy(RuntimeError):
    pass


class ConversationService:
    def __init__(
        self,
        repository: ConversationRepository,
        *,
        soft_token_limit: int,
        hard_token_limit: int,
    ) -> None:
        self.repository = repository
        self.soft_token_limit = soft_token_limit
        self.hard_token_limit = hard_token_limit
        self._lock_guard = Lock()
        self._conversation_locks: dict[str, RLock] = {}

    def close(self) -> None:
        self.repository.close()

    def get_default(self, user_id: str) -> ConversationSnapshot:
        conversation = self.repository.get_or_create_default(
            user_id,
            soft_token_limit=self.soft_token_limit,
            hard_token_limit=self.hard_token_limit,
        )
        return self.get_snapshot(conversation.conversation_id, user_id)

    def get_snapshot(self, conversation_id: str, user_id: str) -> ConversationSnapshot:
        return ConversationSnapshot(
            conversation=self.repository.get_owned(conversation_id, user_id),
            messages=self.repository.list_messages(conversation_id, user_id),
            context_memories=self.repository.list_context_memories(conversation_id, user_id),
        )

    def list_conversations(self, user_id: str) -> list[Conversation]:
        return self.repository.list_conversations(user_id)

    def create_continuation(
        self,
        user_id: str,
        *,
        continued_from_conversation_id: str | None,
        memory_ids: list[str],
        title: str = "新的学习对话",
    ) -> ConversationSnapshot:
        if continued_from_conversation_id:
            self.repository.get_owned(continued_from_conversation_id, user_id)
        conversation = self.repository.create_conversation(
            user_id,
            title=title,
            make_default=True,
            continued_from_public_id=continued_from_conversation_id,
            memory_ids=memory_ids,
            soft_token_limit=self.soft_token_limit,
            hard_token_limit=self.hard_token_limit,
        )
        return self.get_snapshot(conversation.conversation_id, user_id)

    def memory_candidates(self, user_id: str, conversation_id: str | None = None) -> list[MemoryItem]:
        if conversation_id:
            self.repository.get_owned(conversation_id, user_id)
        return self.repository.list_memory_candidates(user_id, conversation_id)

    def append_user_message(
        self,
        conversation_id: str,
        user_id: str,
        *,
        content: str,
        run_id: str,
        question_id: str | None,
        question_title: str | None,
        context_snapshot: dict[str, Any],
    ) -> ConversationMessage:
        with self.lock_for(conversation_id):
            conversation = self.repository.get_owned(conversation_id, user_id)
            if conversation.status is not ConversationStatus.ACTIVE or not conversation.is_default:
                raise ConversationLimitReached("历史 Chat 只能查看，请在当前默认 Chat 中继续。")
            if conversation.hard_limit_reached:
                raise ConversationLimitReached("当前 Chat 已达到上下文上限，请审核记忆后在新的 Chat 中继续。")
            token_estimate = estimate_tokens(content) + estimate_tokens(
                json.dumps(context_snapshot, ensure_ascii=False, separators=(",", ":"))
            )
            return self.repository.append_message(
                conversation_id,
                user_id,
                role=MessageRole.USER,
                content=content,
                run_id=run_id,
                question_id=question_id,
                question_title=question_title,
                context_snapshot=context_snapshot,
                artifact=None,
                token_estimate=token_estimate,
                status=MessageStatus.COMPLETE,
            )

    def ensure_can_continue(self, conversation_id: str, user_id: str) -> Conversation:
        conversation = self.repository.get_owned(conversation_id, user_id)
        if conversation.status is not ConversationStatus.ACTIVE or not conversation.is_default:
            raise ConversationLimitReached("历史 Chat 只能查看，请在当前默认 Chat 中继续。")
        if conversation.hard_limit_reached:
            raise ConversationLimitReached("当前 Chat 已达到上下文上限，请审核记忆后在新的 Chat 中继续。")
        return conversation

    def append_assistant_message(
        self,
        conversation_id: str,
        user_id: str,
        *,
        content: str,
        run_id: str,
        question_id: str | None,
        question_title: str | None,
        artifact: dict[str, Any],
        failed: bool = False,
    ) -> ConversationMessage:
        with self.lock_for(conversation_id):
            return self.repository.append_message(
                conversation_id,
                user_id,
                role=MessageRole.ASSISTANT,
                content=content,
                run_id=run_id,
                question_id=question_id,
                question_title=question_title,
                context_snapshot={},
                artifact=artifact,
                token_estimate=estimate_tokens(content),
                status=MessageStatus.FAILED if failed else MessageStatus.COMPLETE,
            )

    def record_memory_candidates(
        self,
        user_id: str,
        conversation_id: str,
        source_message_id: str | None,
        candidates: list[dict[str, Any]],
    ) -> list[MemoryItem]:
        recorded: list[MemoryItem] = []
        for raw in candidates[:5]:
            content = str(raw.get("content") or "").strip()
            if not content:
                continue
            recorded.append(
                self.repository.create_memory_candidate(
                    user_id,
                    memory_type=str(raw.get("memory_type") or "learning_observation"),
                    content=content,
                    reason=str(raw.get("reason") or "").strip() or None,
                    confidence=_confidence(raw.get("confidence")),
                    source_conversation_id=conversation_id,
                    source_message_id=source_message_id,
                )
            )
        return recorded

    def context_memories(self, conversation_id: str, user_id: str) -> list[MemoryItem]:
        return self.repository.list_context_memories(conversation_id, user_id)

    def record_runtime_tool_decisions(
        self,
        user_id: str,
        conversation_id: str,
        run_id: str,
        decisions: list[dict[str, Any]],
    ) -> list[ToolApproval]:
        recorded: list[ToolApproval] = []
        for raw in decisions[:20]:
            request = ToolActionRequest(
                tool_name=str(raw.get("tool_name") or "unknown"),
                action=str(raw.get("action") or "unknown"),
                resource=str(raw["resource"]) if raw.get("resource") is not None else None,
                arguments=dict(raw.get("arguments") or {}),
            )
            policy = evaluate_tool_request(request)
            recorded.append(
                self.repository.create_tool_approval(
                    user_id,
                    conversation_public_id=conversation_id,
                    run_id=run_id,
                    request=request,
                    policy=policy,
                    status=ToolApprovalStatus.DENIED,
                    hermes_run_id=str(raw.get("hermes_run_id") or "") or None,
                    hermes_request_id=str(raw.get("hermes_request_id") or "") or None,
                )
            )
        return recorded

    def record_model_tool_requests(
        self,
        user_id: str,
        conversation_id: str,
        run_id: str,
        requests: list[dict[str, Any]],
        *,
        suppress_resolved_duplicates: bool = False,
    ) -> list[ToolApproval]:
        recorded: list[ToolApproval] = []
        previous = (
            self.repository.list_tool_approvals(user_id, run_id=run_id)
            if suppress_resolved_duplicates
            else []
        )
        for raw in requests[:5]:
            request = ToolActionRequest(
                tool_name=str(raw.get("tool_name") or "unknown"),
                action=str(raw.get("action") or "unknown"),
                resource=str(raw["resource"]) if raw.get("resource") is not None else None,
                arguments=dict(raw.get("arguments") or {}),
            )
            duplicate = _find_resolved_tool_duplicate(previous, request, allow_unpinned_github=True)
            if duplicate is not None:
                recorded.append(duplicate)
                continue
            result: dict[str, Any] | None = None
            if request.tool_name in {"github.inspect_repository", "github.download_snapshot"}:
                try:
                    request, result = prepare_github_snapshot_request(request)
                    policy = evaluate_tool_request(request)
                except GitHubRepositoryError as exc:
                    policy = ToolPolicyResult(
                        decision=ToolPolicyDecision.BLOCK,
                        risk_level=ToolRiskLevel.PROHIBITED,
                        reason=str(exc),
                    )
            else:
                policy = evaluate_tool_request(request)

            duplicate = _find_resolved_tool_duplicate(previous, request)
            if duplicate is not None:
                recorded.append(duplicate)
                continue

            if policy.decision is ToolPolicyDecision.ASK_USER:
                status = ToolApprovalStatus.PENDING
                ttl_seconds = int(policy.constraints.get("ttlSeconds") or 300)
                expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=ttl_seconds)
            elif policy.decision is ToolPolicyDecision.AUTO_ALLOW and result is not None:
                status = ToolApprovalStatus.EXECUTED
                expires_at = None
            else:
                status = ToolApprovalStatus.DENIED
                expires_at = None

            created = self.repository.create_tool_approval(
                user_id,
                conversation_public_id=conversation_id,
                run_id=run_id,
                request=request,
                policy=policy,
                status=status,
                expires_at=expires_at,
                result=result,
            )
            recorded.append(created)
            previous.append(created)
        return recorded

    def list_tool_approvals(
        self,
        user_id: str,
        *,
        run_id: str | None = None,
        conversation_id: str | None = None,
    ) -> list[ToolApproval]:
        return self.repository.list_tool_approvals(
            user_id,
            run_id=run_id,
            conversation_public_id=conversation_id,
        )

    def active_tool_context(self, conversation_id: str, user_id: str) -> list[dict[str, Any]]:
        approvals = self.repository.list_tool_approvals(
            user_id,
            conversation_public_id=conversation_id,
        )
        data_dir = Path(load_settings().runtime_data_dir)
        context: list[dict[str, Any]] = []
        for approval in approvals:
            if approval.status is not ToolApprovalStatus.EXECUTED or not approval.result:
                continue
            if approval.expires_at and _is_expired(approval.expires_at):
                continue
            item = {
                "approval_id": approval.approval_id,
                "tool_name": approval.tool_name,
                "resource": approval.resource,
                "result": approval.result,
            }
            if approval.tool_name == "github.download_snapshot":
                item["text_excerpts"] = _read_snapshot_excerpts(data_dir, approval)
            context.append(item)
        return context

    def approve_tool(self, user_id: str, approval_id: str) -> ToolApproval:
        approval = self.repository.get_tool_approval_owned(approval_id, user_id)
        if approval.status is ToolApprovalStatus.EXECUTED:
            return approval
        if approval.status is not ToolApprovalStatus.PENDING:
            raise ValueError("审批已处理，不能重复操作。")
        if approval.expires_at and _is_expired(approval.expires_at):
            self.repository.resolve_tool_approval(
                approval_id,
                user_id,
                status=ToolApprovalStatus.EXPIRED,
            )
        request = ToolActionRequest(
            tool_name=approval.tool_name,
            action=approval.action,
            resource=approval.resource,
            arguments=approval.arguments,
        )
        policy = evaluate_tool_request(request)
        if policy.decision is not ToolPolicyDecision.ASK_USER:
            raise PermissionError("当前工具请求不再满足一次性审批策略。")
        if request.tool_name != "github.download_snapshot":
            raise NotImplementedError("当前仅支持受控 GitHub 快照下载。")
        result = download_github_snapshot(
            request,
            approval_id=approval.approval_id,
            data_dir=Path(load_settings().runtime_data_dir),
            constraints=policy.constraints,
        )
        return self.repository.resolve_tool_approval(
            approval_id,
            user_id,
            status=ToolApprovalStatus.EXECUTED,
            result=result,
        )

    def deny_tool(self, user_id: str, approval_id: str) -> ToolApproval:
        approval = self.repository.get_tool_approval_owned(approval_id, user_id)
        if approval.status is ToolApprovalStatus.DENIED:
            return approval
        if approval.status is not ToolApprovalStatus.PENDING:
            raise ValueError("审批已处理，不能重复操作。")
        return self.repository.resolve_tool_approval(
            approval_id,
            user_id,
            status=ToolApprovalStatus.DENIED,
        )

    def lock_for(self, conversation_id: str) -> RLock:
        with self._lock_guard:
            return self._conversation_locks.setdefault(conversation_id, RLock())

    @contextmanager
    def serialized(self, conversation_id: str, user_id: str):
        with self.lock_for(conversation_id):
            with self.repository.execution_lock(conversation_id, user_id) as acquired:
                if not acquired:
                    raise ConversationBusy("当前 Chat 正在处理另一条消息，请稍后重试。")
                yield


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text.encode("utf-8")) / 3))


def _confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    return 0.5


def _find_resolved_tool_duplicate(
    approvals: list[ToolApproval],
    request: ToolActionRequest,
    *,
    allow_unpinned_github: bool = False,
) -> ToolApproval | None:
    requested_repository = normalize_public_github_repository(request.resource)
    requested_sha = str(request.arguments.get("commit_sha") or "").strip().lower()
    for approval in approvals:
        if approval.status is ToolApprovalStatus.PENDING:
            continue
        if approval.tool_name != request.tool_name or approval.action != request.action:
            continue
        if approval.resource == request.resource and approval.arguments == request.arguments:
            return approval
        if (
            allow_unpinned_github
            and request.tool_name == "github.download_snapshot"
            and not requested_sha
            and requested_repository is not None
            and normalize_public_github_repository(approval.resource) == requested_repository
        ):
            return approval
    return None


def _is_expired(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed <= datetime.now(timezone.utc)


def _read_snapshot_excerpts(data_dir: Path, approval: ToolApproval) -> list[dict[str, str]]:
    result = approval.result or {}
    samples = result.get("fileSample")
    if not isinstance(samples, list):
        return []
    root = (data_dir / "github-snapshots" / approval.approval_id / "files").resolve()
    if not root.is_dir():
        return []
    allowed_names = {"readme", "license", "makefile", "dockerfile", "package.json", "pyproject.toml"}
    allowed_suffixes = {".md", ".txt", ".py", ".ts", ".tsx", ".js", ".java", ".go", ".rs", ".json", ".toml", ".yaml", ".yml"}
    candidates = sorted(
        (str(item) for item in samples if isinstance(item, str)),
        key=lambda item: (0 if Path(item).name.casefold().startswith("readme") else 1, item),
    )
    excerpts: list[dict[str, str]] = []
    total_chars = 0
    for relative in candidates:
        relative_path = Path(relative)
        lowered_name = relative_path.name.casefold()
        if any(part.startswith(".") for part in relative_path.parts):
            continue
        if lowered_name not in allowed_names and relative_path.suffix.casefold() not in allowed_suffixes:
            continue
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > 64 * 1024:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "\0" in content:
            continue
        remaining = 18000 - total_chars
        if remaining <= 0:
            break
        excerpt = content[: min(6000, remaining)]
        excerpts.append({"path": relative_path.as_posix(), "content": excerpt})
        total_chars += len(excerpt)
        if len(excerpts) >= 5:
            break
    return excerpts


_service_lock = Lock()
_service: ConversationService | None = None
_service_database_url: str | None = None


def get_conversation_service() -> ConversationService:
    global _service, _service_database_url
    explicit_database_url = os.getenv("OJ_AGENT_DATABASE_URL")
    with _service_lock:
        if _service is not None and explicit_database_url and _service_database_url == explicit_database_url:
            return _service
    settings = load_settings()
    database_url = settings.database_url or "sqlite+pysqlite:///:memory:"
    with _service_lock:
        if _service is None or _service_database_url != database_url:
            if _service is not None:
                _service.close()
            _service = ConversationService(
                ConversationRepository(database_url),
                soft_token_limit=settings.conversation_soft_token_limit,
                hard_token_limit=settings.conversation_hard_token_limit,
            )
            _service_database_url = database_url
        return _service


def reset_conversation_service() -> None:
    global _service, _service_database_url
    with _service_lock:
        if _service is not None:
            _service.close()
        _service = None
        _service_database_url = None
