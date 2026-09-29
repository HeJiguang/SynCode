from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, create_engine, select, text
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.domain.conversations import (
    Conversation,
    ConversationMessage,
    ConversationStatus,
    MemoryItem,
    MemoryStatus,
    MessageRole,
    MessageStatus,
)
from app.domain.tool_permissions import (
    ToolActionRequest,
    ToolApproval,
    ToolApprovalStatus,
    ToolPolicyResult,
)


IdColumn = BIGINT(unsigned=True).with_variant(Integer, "sqlite")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class ConversationRecord(Base):
    __tablename__ = "tb_ai_conversation"
    __table_args__ = (
        UniqueConstraint("conversation_key", name="uk_ai_conversation_key"),
        UniqueConstraint("public_id", name="uk_ai_conversation_public_id"),
        UniqueConstraint("user_id", "default_slot", name="uk_ai_conversation_user_default"),
        Index("idx_ai_conversation_user_updated", "user_id", "updated_at"),
    )

    conversation_id: Mapped[int] = mapped_column(IdColumn, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), nullable=False)
    conversation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=ConversationStatus.ACTIVE.value)
    default_slot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_question_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_question_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    continued_from_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    context_token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    soft_token_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    hard_token_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utc_now)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class MessageRecord(Base):
    __tablename__ = "tb_ai_message"
    __table_args__ = (
        UniqueConstraint("public_id", name="uk_ai_message_public_id"),
        UniqueConstraint("conversation_id", "sequence_no", name="uk_ai_message_conversation_seq"),
        Index("idx_ai_message_run", "run_id"),
    )

    message_id: Mapped[int] = mapped_column(IdColumn, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), nullable=False)
    conversation_id: Mapped[int] = mapped_column(IdColumn, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    question_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    artifact_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=MessageStatus.COMPLETE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utc_now)


class MemoryRecord(Base):
    __tablename__ = "tb_ai_memory"
    __table_args__ = (
        UniqueConstraint("public_id", name="uk_ai_memory_public_id"),
        Index("idx_ai_memory_user_status", "user_id", "status", "created_at"),
    )

    memory_id: Mapped[int] = mapped_column(IdColumn, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=MemoryStatus.PENDING.value)
    source_conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utc_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class ConversationMemoryRecord(Base):
    __tablename__ = "tb_ai_conversation_memory"
    __table_args__ = (
        UniqueConstraint("conversation_id", "memory_id", name="uk_ai_conversation_memory"),
    )

    binding_id: Mapped[int] = mapped_column(IdColumn, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(IdColumn, nullable=False)
    memory_id: Mapped[int] = mapped_column(IdColumn, nullable=False)
    content_snapshot: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utc_now)


class ToolApprovalRecord(Base):
    __tablename__ = "tb_ai_tool_approval"
    __table_args__ = (
        UniqueConstraint("public_id", name="uk_ai_tool_approval_public_id"),
        UniqueConstraint("hermes_run_id", "hermes_request_id", name="uk_ai_tool_approval_remote_request"),
        Index("idx_ai_tool_approval_user_status", "user_id", "status", "created_at"),
    )

    approval_id: Mapped[int] = mapped_column(IdColumn, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    conversation_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    hermes_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hermes_request_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    arguments_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class RunRecord(Base):
    __tablename__ = "tb_ai_run"
    __table_args__ = (
        UniqueConstraint("public_id", name="uk_ai_run_public_id"),
        Index("idx_ai_run_user_created", "user_id", "created_at"),
        Index("idx_ai_run_conversation_created", "conversation_public_id", "created_at"),
    )

    run_pk: Mapped[int] = mapped_column(IdColumn, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    conversation_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    run_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_graph: Mapped[str] = mapped_column(String(120), nullable=False)
    active_node: Mapped[str | None] = mapped_column(String(120), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    context_ref_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    request_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class RunEventRecord(Base):
    __tablename__ = "tb_ai_run_event"
    __table_args__ = (
        UniqueConstraint("public_id", name="uk_ai_run_event_public_id"),
        UniqueConstraint("run_public_id", "sequence_no", name="uk_ai_run_event_run_seq"),
        Index("idx_ai_run_event_run_created", "run_public_id", "created_at"),
    )

    event_pk: Mapped[int] = mapped_column(IdColumn, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_public_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utc_now)


class ArtifactRecord(Base):
    __tablename__ = "tb_ai_artifact"
    __table_args__ = (
        UniqueConstraint("public_id", name="uk_ai_artifact_public_id"),
        Index("idx_ai_artifact_run_created", "run_public_id", "created_at"),
    )

    artifact_pk: Mapped[int] = mapped_column(IdColumn, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_public_id: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    body_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    render_hint: Mapped[str] = mapped_column(String(48), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utc_now)


class ConversationRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        if database_url.startswith("sqlite"):
            database_path = database_url.rsplit("///", 1)[-1]
            if database_path and database_path != ":memory:":
                Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)
        if database_url.startswith("sqlite"):
            Base.metadata.create_all(self.engine)

    def close(self) -> None:
        self.engine.dispose()

    @contextmanager
    def execution_lock(self, public_id: str, user_id: str):
        if self.engine.dialect.name != "mysql":
            yield True
            return

        digest = hashlib.sha256(f"{user_id}\0{public_id}".encode("utf-8")).hexdigest()[:40]
        with self._named_lock(f"syncode-chat:{digest}") as acquired:
            yield acquired

    @contextmanager
    def user_admission_lock(self, user_id: str):
        if self.engine.dialect.name != "mysql":
            yield True
            return

        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:40]
        with self._named_lock(f"syncode-user-admission:{digest}") as acquired:
            yield acquired

    @contextmanager
    def _named_lock(self, lock_name: str):
        with self.engine.connect() as connection:
            acquired = connection.scalar(
                text("SELECT GET_LOCK(:lock_name, 0)"),
                {"lock_name": lock_name},
            )
            try:
                yield acquired == 1
            finally:
                if acquired == 1:
                    connection.execute(
                        text("SELECT RELEASE_LOCK(:lock_name)"),
                        {"lock_name": lock_name},
                    )

    def get_or_create_default(
        self,
        user_id: str,
        *,
        soft_token_limit: int,
        hard_token_limit: int,
    ) -> Conversation:
        with self.session_factory.begin() as session:
            record = session.scalar(
                select(ConversationRecord).where(
                    ConversationRecord.user_id == user_id,
                    ConversationRecord.default_slot == 1,
                    ConversationRecord.status == ConversationStatus.ACTIVE.value,
                )
            )
            if record is None:
                record = self._new_conversation_record(
                    user_id,
                    title="学习主线",
                    make_default=True,
                    soft_token_limit=soft_token_limit,
                    hard_token_limit=hard_token_limit,
                )
                session.add(record)
                session.flush()
            return self._conversation_model(record)

    def create_conversation(
        self,
        user_id: str,
        *,
        title: str,
        make_default: bool,
        continued_from_public_id: str | None,
        memory_ids: list[str],
        soft_token_limit: int,
        hard_token_limit: int,
    ) -> Conversation:
        with self.session_factory.begin() as session:
            if make_default:
                previous = session.scalar(
                    select(ConversationRecord).where(
                        ConversationRecord.user_id == user_id,
                        ConversationRecord.default_slot == 1,
                    ).with_for_update()
                )
                if previous is not None:
                    previous.default_slot = None
                    previous.conversation_key = f"{user_id}:{previous.public_id}"
                    if previous.status == ConversationStatus.ACTIVE.value:
                        previous.status = ConversationStatus.ROLLED_OVER.value
                    previous.updated_at = utc_now()
                    session.flush()

            record = self._new_conversation_record(
                user_id,
                title=title,
                make_default=make_default,
                continued_from_public_id=continued_from_public_id,
                soft_token_limit=soft_token_limit,
                hard_token_limit=hard_token_limit,
            )
            session.add(record)
            session.flush()
            self._approve_and_bind_memories(session, record, user_id, memory_ids)
            return self._conversation_model(record)

    def list_conversations(self, user_id: str) -> list[Conversation]:
        with self.session_factory() as session:
            records = session.scalars(
                select(ConversationRecord)
                .where(ConversationRecord.user_id == user_id)
                .order_by(ConversationRecord.updated_at.desc())
            ).all()
            return [self._conversation_model(record) for record in records]

    def get_owned(self, public_id: str, user_id: str) -> Conversation:
        with self.session_factory() as session:
            record = self._owned_record(session, public_id, user_id)
            return self._conversation_model(record)

    def list_messages(self, public_id: str, user_id: str) -> list[ConversationMessage]:
        with self.session_factory() as session:
            conversation = self._owned_record(session, public_id, user_id)
            records = session.scalars(
                select(MessageRecord)
                .where(MessageRecord.conversation_id == conversation.conversation_id)
                .order_by(MessageRecord.sequence_no.asc())
            ).all()
            return [self._message_model(record, public_id) for record in records]

    def append_message(
        self,
        public_id: str,
        user_id: str,
        *,
        role: MessageRole,
        content: str,
        run_id: str | None,
        question_id: str | None,
        question_title: str | None,
        context_snapshot: dict[str, Any],
        artifact: dict[str, Any] | None,
        token_estimate: int,
        status: MessageStatus,
    ) -> ConversationMessage:
        with self.session_factory.begin() as session:
            conversation = self._owned_record(session, public_id, user_id, for_update=True)
            now = utc_now()
            sequence = conversation.message_count + 1
            message = MessageRecord(
                public_id=f"msg_{uuid4().hex}",
                conversation_id=conversation.conversation_id,
                user_id=user_id,
                run_id=run_id,
                role=role.value,
                content=content,
                sequence_no=sequence,
                question_id=question_id,
                context_snapshot=context_snapshot,
                artifact_json=artifact,
                token_estimate=max(token_estimate, 0),
                status=status.value,
                created_at=now,
            )
            session.add(message)
            conversation.message_count = sequence
            conversation.context_token_estimate += max(token_estimate, 0)
            conversation.current_question_id = question_id or conversation.current_question_id
            conversation.current_question_title = question_title or conversation.current_question_title
            conversation.last_message_at = now
            conversation.updated_at = now
            session.flush()
            return self._message_model(message, public_id)

    def create_memory_candidate(
        self,
        user_id: str,
        *,
        memory_type: str,
        content: str,
        reason: str | None,
        confidence: float,
        source_conversation_id: str,
        source_message_id: str | None,
    ) -> MemoryItem:
        with self.session_factory.begin() as session:
            self._owned_record(session, source_conversation_id, user_id)
            record = MemoryRecord(
                public_id=f"mem_{uuid4().hex}",
                user_id=user_id,
                memory_type=memory_type[:40],
                content=content[:1000],
                reason=(reason or "")[:500] or None,
                confidence=max(0.0, min(float(confidence), 1.0)),
                status=MemoryStatus.PENDING.value,
                source_conversation_id=source_conversation_id,
                source_message_id=source_message_id,
            )
            session.add(record)
            session.flush()
            return self._memory_model(record)

    def list_memory_candidates(self, user_id: str, source_conversation_id: str | None = None) -> list[MemoryItem]:
        with self.session_factory() as session:
            query = select(MemoryRecord).where(
                MemoryRecord.user_id == user_id,
                MemoryRecord.status.in_([MemoryStatus.PENDING.value, MemoryStatus.APPROVED.value]),
            )
            if source_conversation_id:
                query = query.where(
                    (MemoryRecord.source_conversation_id == source_conversation_id)
                    | (MemoryRecord.status == MemoryStatus.APPROVED.value)
                )
            records = session.scalars(query.order_by(MemoryRecord.created_at.desc())).all()
            return [self._memory_model(record) for record in records]

    def list_context_memories(self, public_id: str, user_id: str) -> list[MemoryItem]:
        with self.session_factory() as session:
            conversation = self._owned_record(session, public_id, user_id)
            records = session.scalars(
                select(MemoryRecord)
                .join(ConversationMemoryRecord, ConversationMemoryRecord.memory_id == MemoryRecord.memory_id)
                .where(
                    ConversationMemoryRecord.conversation_id == conversation.conversation_id,
                    MemoryRecord.user_id == user_id,
                    MemoryRecord.status == MemoryStatus.APPROVED.value,
                )
                .order_by(MemoryRecord.created_at.asc())
            ).all()
            return [self._memory_model(record) for record in records]

    def create_tool_approval(
        self,
        user_id: str,
        *,
        conversation_public_id: str | None,
        run_id: str,
        request: ToolActionRequest,
        policy: ToolPolicyResult,
        status: ToolApprovalStatus,
        hermes_run_id: str | None = None,
        hermes_request_id: str | None = None,
        expires_at: datetime | None = None,
        result: dict[str, Any] | None = None,
    ) -> ToolApproval:
        with self.session_factory.begin() as session:
            if conversation_public_id:
                self._owned_record(session, conversation_public_id, user_id)
            if hermes_run_id and hermes_request_id:
                existing = session.scalar(
                    select(ToolApprovalRecord).where(
                        ToolApprovalRecord.hermes_run_id == hermes_run_id,
                        ToolApprovalRecord.hermes_request_id == hermes_request_id,
                    )
                )
                if existing is not None:
                    if existing.user_id != user_id:
                        raise KeyError(hermes_request_id)
                    return self._tool_approval_model(existing)
            record = ToolApprovalRecord(
                public_id=f"approval_{uuid4().hex}",
                user_id=user_id,
                conversation_public_id=conversation_public_id,
                run_id=run_id,
                hermes_run_id=hermes_run_id,
                hermes_request_id=hermes_request_id,
                tool_name=request.tool_name[:120],
                action=request.action[:120],
                resource=(request.resource or policy.normalized_resource or "")[:1000] or None,
                arguments_json={
                    "request": dict(request.arguments),
                    "constraints": dict(policy.constraints),
                    "result": dict(result) if result else None,
                },
                risk_level=policy.risk_level.value,
                decision=policy.decision.value,
                status=status.value,
                reason=policy.reason[:500],
                expires_at=expires_at,
                resolved_at=utc_now() if status is not ToolApprovalStatus.PENDING else None,
            )
            session.add(record)
            session.flush()
            return self._tool_approval_model(record)

    def get_tool_approval_owned(self, public_id: str, user_id: str, *, for_update: bool = False) -> ToolApproval:
        with self.session_factory() as session:
            query = select(ToolApprovalRecord).where(
                ToolApprovalRecord.public_id == public_id,
                ToolApprovalRecord.user_id == user_id,
            )
            if for_update:
                query = query.with_for_update()
            record = session.scalar(query)
            if record is None:
                raise KeyError(public_id)
            return self._tool_approval_model(record)

    def resolve_tool_approval(
        self,
        public_id: str,
        user_id: str,
        *,
        status: ToolApprovalStatus,
        result: dict[str, Any] | None = None,
    ) -> ToolApproval:
        with self.session_factory.begin() as session:
            record = session.scalar(
                select(ToolApprovalRecord)
                .where(
                    ToolApprovalRecord.public_id == public_id,
                    ToolApprovalRecord.user_id == user_id,
                )
                .with_for_update()
            )
            if record is None:
                raise KeyError(public_id)
            if record.status != ToolApprovalStatus.PENDING.value:
                raise ValueError("审批已处理，不能重复操作。")
            now = utc_now()
            if record.expires_at is not None and record.expires_at <= now:
                record.status = ToolApprovalStatus.EXPIRED.value
                record.resolved_at = now
                session.flush()
                raise TimeoutError("审批已过期，请重新发起请求。")
            payload = dict(record.arguments_json or {})
            if result is not None:
                payload["result"] = dict(result)
                record.arguments_json = payload
            record.status = status.value
            record.resolved_at = now
            session.flush()
            return self._tool_approval_model(record)

    def list_tool_approvals(
        self,
        user_id: str,
        *,
        run_id: str | None = None,
        conversation_public_id: str | None = None,
    ) -> list[ToolApproval]:
        with self.session_factory() as session:
            query = select(ToolApprovalRecord).where(ToolApprovalRecord.user_id == user_id)
            if run_id:
                query = query.where(ToolApprovalRecord.run_id == run_id)
            if conversation_public_id:
                self._owned_record(session, conversation_public_id, user_id)
                query = query.where(ToolApprovalRecord.conversation_public_id == conversation_public_id)
            records = session.scalars(query.order_by(ToolApprovalRecord.created_at.asc())).all()
            return [self._tool_approval_model(record) for record in records]

    def _approve_and_bind_memories(
        self,
        session: Session,
        conversation: ConversationRecord,
        user_id: str,
        memory_ids: list[str],
    ) -> None:
        if not memory_ids:
            return
        records = session.scalars(
            select(MemoryRecord).where(
                MemoryRecord.user_id == user_id,
                MemoryRecord.public_id.in_(memory_ids),
            ).with_for_update()
        ).all()
        if len(records) != len(set(memory_ids)):
            raise KeyError("One or more memory items do not belong to the current user.")
        now = utc_now()
        for memory in records:
            memory.status = MemoryStatus.APPROVED.value
            memory.reviewed_at = now
            session.add(
                ConversationMemoryRecord(
                    conversation_id=conversation.conversation_id,
                    memory_id=memory.memory_id,
                    content_snapshot=memory.content,
                )
            )

    @staticmethod
    def _new_conversation_record(
        user_id: str,
        *,
        title: str,
        make_default: bool,
        soft_token_limit: int,
        hard_token_limit: int,
        continued_from_public_id: str | None = None,
    ) -> ConversationRecord:
        public_id = f"conv_{uuid4().hex}"
        return ConversationRecord(
            public_id=public_id,
            conversation_key=f"{user_id}:{'default' if make_default else public_id}",
            user_id=user_id,
            title=title[:160] or "新的学习对话",
            status=ConversationStatus.ACTIVE.value,
            default_slot=1 if make_default else None,
            continued_from_public_id=continued_from_public_id,
            soft_token_limit=max(soft_token_limit, 1),
            hard_token_limit=max(hard_token_limit, soft_token_limit + 1),
        )

    @staticmethod
    def _owned_record(
        session: Session,
        public_id: str,
        user_id: str,
        *,
        for_update: bool = False,
    ) -> ConversationRecord:
        query = select(ConversationRecord).where(
            ConversationRecord.public_id == public_id,
            ConversationRecord.user_id == user_id,
        )
        if for_update:
            query = query.with_for_update()
        record = session.scalar(query)
        if record is None:
            raise KeyError(public_id)
        return record

    @staticmethod
    def _conversation_model(record: ConversationRecord) -> Conversation:
        return Conversation(
            conversation_id=record.public_id,
            user_id=record.user_id,
            title=record.title,
            status=ConversationStatus(record.status),
            is_default=record.default_slot == 1,
            current_question_id=record.current_question_id,
            current_question_title=record.current_question_title,
            continued_from_conversation_id=record.continued_from_public_id,
            message_count=record.message_count,
            context_token_estimate=record.context_token_estimate,
            soft_token_limit=record.soft_token_limit,
            hard_token_limit=record.hard_token_limit,
            created_at=iso_timestamp(record.created_at) or "",
            updated_at=iso_timestamp(record.updated_at) or "",
            last_message_at=iso_timestamp(record.last_message_at),
        )

    @staticmethod
    def _message_model(record: MessageRecord, conversation_public_id: str) -> ConversationMessage:
        return ConversationMessage(
            message_id=record.public_id,
            conversation_id=conversation_public_id,
            run_id=record.run_id,
            role=MessageRole(record.role),
            content=record.content,
            sequence=record.sequence_no,
            question_id=record.question_id,
            context_snapshot=dict(record.context_snapshot or {}),
            artifact=dict(record.artifact_json) if record.artifact_json else None,
            token_estimate=record.token_estimate,
            status=MessageStatus(record.status),
            created_at=iso_timestamp(record.created_at) or "",
        )

    @staticmethod
    def _memory_model(record: MemoryRecord) -> MemoryItem:
        return MemoryItem(
            memory_id=record.public_id,
            user_id=record.user_id,
            memory_type=record.memory_type,
            content=record.content,
            reason=record.reason,
            confidence=record.confidence,
            status=MemoryStatus(record.status),
            source_conversation_id=record.source_conversation_id,
            source_message_id=record.source_message_id,
            created_at=iso_timestamp(record.created_at) or "",
            reviewed_at=iso_timestamp(record.reviewed_at),
        )

    @staticmethod
    def _tool_approval_model(record: ToolApprovalRecord) -> ToolApproval:
        payload = dict(record.arguments_json or {})
        arguments = payload.get("request")
        constraints = payload.get("constraints")
        result = payload.get("result")
        return ToolApproval(
            approval_id=record.public_id,
            user_id=record.user_id,
            conversation_id=record.conversation_public_id,
            run_id=record.run_id,
            hermes_run_id=record.hermes_run_id,
            hermes_request_id=record.hermes_request_id,
            tool_name=record.tool_name,
            action=record.action,
            resource=record.resource,
            arguments=dict(arguments) if isinstance(arguments, dict) else {},
            constraints=dict(constraints) if isinstance(constraints, dict) else {},
            result=dict(result) if isinstance(result, dict) else None,
            risk_level=record.risk_level,
            decision=record.decision,
            status=record.status,
            reason=record.reason,
            created_at=iso_timestamp(record.created_at) or "",
            expires_at=iso_timestamp(record.expires_at),
            resolved_at=iso_timestamp(record.resolved_at),
        )
