from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.conversations.repository import ArtifactRecord, ConversationRepository, iso_timestamp, utc_now
from app.domain.artifacts import Artifact, ArtifactType, RenderHint


class ArtifactStore:
    """SQL-backed artifact repository keyed by public Run id."""

    def __init__(
        self,
        repository_provider: Callable[[], ConversationRepository] | None = None,
    ) -> None:
        self._repository_provider = repository_provider

    def append(self, artifact: Artifact) -> Artifact:
        repository = self._repository()
        with repository.session_factory.begin() as session:
            existing = session.scalar(
                select(ArtifactRecord).where(ArtifactRecord.public_id == artifact.artifact_id)
            )
            if existing is not None:
                return self._artifact_model(existing)
            record = ArtifactRecord(
                public_id=artifact.artifact_id,
                run_public_id=artifact.run_id,
                artifact_type=artifact.artifact_type.value,
                title=artifact.title,
                summary=artifact.summary,
                body_json=dict(artifact.body),
                render_hint=artifact.render_hint.value,
                version=artifact.version,
                created_at=_parse_timestamp(artifact.created_at) or utc_now(),
            )
            session.add(record)
            session.flush()
            return self._artifact_model(record)

    def list_for_run(self, run_id: str) -> list[Artifact]:
        repository = self._repository()
        with repository.session_factory() as session:
            records = session.scalars(
                select(ArtifactRecord)
                .where(ArtifactRecord.run_public_id == run_id)
                .order_by(ArtifactRecord.created_at.asc(), ArtifactRecord.artifact_pk.asc())
            ).all()
            return [self._artifact_model(record) for record in records]

    def clear(self) -> None:
        repository = self._repository()
        with repository.session_factory.begin() as session:
            session.execute(delete(ArtifactRecord))

    def _repository(self) -> ConversationRepository:
        if self._repository_provider is not None:
            return self._repository_provider()
        from app.conversations import get_conversation_service

        return get_conversation_service().repository

    @staticmethod
    def _artifact_model(record: ArtifactRecord) -> Artifact:
        return Artifact(
            artifact_id=record.public_id,
            run_id=record.run_public_id,
            artifact_type=ArtifactType(record.artifact_type),
            title=record.title,
            summary=record.summary,
            body=dict(record.body_json or {}),
            render_hint=RenderHint(record.render_hint),
            version=record.version,
            created_at=iso_timestamp(record.created_at) or "",
        )


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed
