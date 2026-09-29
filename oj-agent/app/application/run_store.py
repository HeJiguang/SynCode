from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import delete, func, select

from app.conversations.repository import (
    ConversationRepository,
    RunEventRecord,
    RunRecord,
    iso_timestamp,
    utc_now,
)
from app.domain.runs import (
    ContextRef,
    EventLevel,
    EventType,
    Run,
    RunEvent,
    RunPriority,
    RunSource,
    RunStatus,
    RunType,
)


class RunStore:
    """SQL-backed run and event repository using the conversation database."""

    def __init__(
        self,
        repository_provider: Callable[[], ConversationRepository] | None = None,
    ) -> None:
        self._repository_provider = repository_provider

    def save(self, run: Run) -> Run:
        repository = self._repository()
        with repository.session_factory.begin() as session:
            record = session.scalar(
                select(RunRecord).where(RunRecord.public_id == run.run_id).with_for_update()
            )
            if record is None:
                record = RunRecord(public_id=run.run_id)
                session.add(record)
            record.user_id = run.user_id
            record.conversation_public_id = run.conversation_id
            record.run_type = run.run_type.value
            record.source = run.source.value
            record.status = run.status.value
            record.entry_graph = run.entry_graph
            record.active_node = run.active_node
            record.priority = run.priority.value
            record.trace_id = run.trace_id
            record.context_ref_json = run.context_ref.model_dump(mode="json")
            record.request_json = dict(run.request_payload)
            record.created_at = _parse_timestamp(run.created_at) or utc_now()
            record.updated_at = utc_now()
            record.completed_at = _parse_timestamp(run.completed_at)
            session.flush()
            return self._run_model(record)

    def get(self, run_id: str) -> Run:
        repository = self._repository()
        with repository.session_factory() as session:
            record = session.scalar(select(RunRecord).where(RunRecord.public_id == run_id))
            if record is None:
                raise KeyError(run_id)
            return self._run_model(record)

    def list_runs(self) -> list[Run]:
        repository = self._repository()
        with repository.session_factory() as session:
            records = session.scalars(select(RunRecord).order_by(RunRecord.created_at.asc())).all()
            return [self._run_model(record) for record in records]

    @contextmanager
    def user_admission_lock(self, user_id: str):
        repository = self._repository()
        with repository.user_admission_lock(user_id) as acquired:
            if not acquired:
                raise TimeoutError("正在处理同一用户的 Agent Run 创建请求。")
            yield

    def count_active_runs(self, user_id: str, *, stale_before: datetime) -> int:
        repository = self._repository()
        active_statuses = [
            RunStatus.QUEUED.value,
            RunStatus.RUNNING.value,
            RunStatus.APPLYING.value,
        ]
        with repository.session_factory() as session:
            return int(
                session.scalar(
                    select(func.count())
                    .select_from(RunRecord)
                    .where(
                        RunRecord.user_id == user_id,
                        RunRecord.status.in_(active_statuses),
                        RunRecord.updated_at >= stale_before,
                    )
                )
                or 0
            )

    def count_runs_since(self, user_id: str, *, since: datetime) -> int:
        repository = self._repository()
        with repository.session_factory() as session:
            return int(
                session.scalar(
                    select(func.count())
                    .select_from(RunRecord)
                    .where(
                        RunRecord.user_id == user_id,
                        RunRecord.created_at >= since,
                    )
                )
                or 0
            )

    def append_event(self, run_id: str, event_type: EventType, payload: dict | None = None) -> RunEvent:
        repository = self._repository()
        with repository.session_factory.begin() as session:
            run_record = session.scalar(
                select(RunRecord).where(RunRecord.public_id == run_id).with_for_update()
            )
            if run_record is None:
                raise KeyError(run_id)
            previous_seq = session.scalar(
                select(func.max(RunEventRecord.sequence_no)).where(
                    RunEventRecord.run_public_id == run_id
                )
            )
            event = RunEvent(
                run_id=run_id,
                seq=int(previous_seq or 0) + 1,
                event_type=event_type,
                payload=dict(payload or {}),
            )
            session.add(
                RunEventRecord(
                    public_id=event.event_id,
                    run_public_id=event.run_id,
                    sequence_no=event.seq,
                    event_type=event.event_type.value,
                    level=event.level.value,
                    payload_json=event.payload,
                    created_at=_parse_timestamp(event.timestamp) or utc_now(),
                )
            )
            return event

    def list_events(self, run_id: str) -> list[RunEvent]:
        repository = self._repository()
        with repository.session_factory() as session:
            records = session.scalars(
                select(RunEventRecord)
                .where(RunEventRecord.run_public_id == run_id)
                .order_by(RunEventRecord.sequence_no.asc())
            ).all()
            return [self._event_model(record) for record in records]

    def update_status(self, run_id: str, status: RunStatus, *, active_node: str | None = None) -> Run:
        repository = self._repository()
        with repository.session_factory.begin() as session:
            record = session.scalar(
                select(RunRecord).where(RunRecord.public_id == run_id).with_for_update()
            )
            if record is None:
                raise KeyError(run_id)
            now = utc_now()
            record.status = status.value
            record.active_node = active_node
            record.updated_at = now
            if status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}:
                record.completed_at = now
            session.flush()
            return self._run_model(record)

    def clear(self) -> None:
        repository = self._repository()
        with repository.session_factory.begin() as session:
            session.execute(delete(RunEventRecord))
            session.execute(delete(RunRecord))

    def _repository(self) -> ConversationRepository:
        if self._repository_provider is not None:
            return self._repository_provider()
        from app.conversations import get_conversation_service

        return get_conversation_service().repository

    @staticmethod
    def _run_model(record: RunRecord) -> Run:
        return Run(
            run_id=record.public_id,
            run_type=RunType(record.run_type),
            source=RunSource(record.source),
            user_id=record.user_id,
            trace_id=record.trace_id,
            conversation_id=record.conversation_public_id,
            status=RunStatus(record.status),
            entry_graph=record.entry_graph,
            active_node=record.active_node,
            priority=RunPriority(record.priority),
            context_ref=ContextRef.model_validate(record.context_ref_json or {}),
            request_payload=dict(record.request_json or {}),
            created_at=iso_timestamp(record.created_at) or "",
            updated_at=iso_timestamp(record.updated_at) or "",
            completed_at=iso_timestamp(record.completed_at),
        )

    @staticmethod
    def _event_model(record: RunEventRecord) -> RunEvent:
        return RunEvent(
            event_id=record.public_id,
            run_id=record.run_public_id,
            seq=record.sequence_no,
            event_type=EventType(record.event_type),
            level=EventLevel(record.level),
            timestamp=iso_timestamp(record.created_at) or "",
            payload=dict(record.payload_json or {}),
        )


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed
