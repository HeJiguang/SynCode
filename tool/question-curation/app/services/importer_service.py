from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.candidate import CandidateProblem, CandidateStatus, UploadStatus
from app.models.import_record import ImportRecord
from app.models.remote_db_config import RemoteDatabaseConfig
from app.schemas.import_preview import ImportPreview
from app.services.remote_db_config_service import RemoteDatabaseConfigService


@dataclass(slots=True)
class BatchImportSummary:
    attempted: int
    imported: int
    failed: int


class ImporterService:
    def __init__(self, settings: Settings, session: Session | None = None) -> None:
        self.settings = settings
        self.session = session

    def build_preview(self, candidate: CandidateProblem) -> ImportPreview:
        return ImportPreview(
            title=candidate.title,
            content=candidate.statement_markdown,
            question_case=candidate.question_case_json or "[]",
            default_code=candidate.default_code_java or "",
            main_fuc=candidate.main_fuc_java or "",
        )

    def import_candidate(
        self,
        candidate: CandidateProblem,
        *,
        database_url: str | None = None,
        remote_config_name: str | None = None,
    ) -> dict[str, str]:
        if candidate.status is not CandidateStatus.APPROVED:
            raise ValueError("Candidate must be approved before import.")

        target_database_url = database_url or self._resolve_database_url()
        if not target_database_url:
            raise ValueError("Remote database is not configured.")

        question_id = self._generate_question_id()
        payload = {
            "question_id": question_id,
            "title": candidate.title,
            "difficulty": candidate.difficulty,
            "algorithm_tag": candidate.algorithm_tag,
            "knowledge_tags": candidate.knowledge_tags,
            "estimated_minutes": candidate.estimated_minutes,
            "training_enabled": 1,
            "time_limit": candidate.time_limit_ms,
            "space_limit": candidate.space_limit_kb,
            "content": candidate.statement_markdown,
            "question_case": candidate.question_case_json or "[]",
            "default_code": candidate.default_code_java or "",
            "main_fuc": candidate.main_fuc_java or "",
            "create_by": self.settings.import_create_by,
            "create_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        engine = create_engine(target_database_url, future=True)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO tb_question (
                        question_id, title, difficulty, algorithm_tag, knowledge_tags,
                        estimated_minutes, training_enabled, time_limit, space_limit,
                        content, question_case, default_code, main_fuc, create_by, create_time
                    ) VALUES (
                        :question_id, :title, :difficulty, :algorithm_tag, :knowledge_tags,
                        :estimated_minutes, :training_enabled, :time_limit, :space_limit,
                        :content, :question_case, :default_code, :main_fuc, :create_by, :create_time
                    )
                    """
                ),
                payload,
            )

        candidate.upload_status = UploadStatus.UPLOADED
        candidate.remote_question_id = str(question_id)
        candidate.upload_error = None
        candidate.status = CandidateStatus.IMPORTED
        self._persist_candidate(candidate)
        self._record_import(
            candidate=candidate,
            import_status="imported",
            target_question_id=question_id,
            remote_config_name=remote_config_name,
            error_message=None,
            sql_snapshot=str(payload),
        )
        return {"status": "imported", "question_id": str(question_id)}

    def batch_import_approved_candidates(self, candidates: list[CandidateProblem]) -> BatchImportSummary:
        target_database_url, config_name = self._resolve_database_url_with_name()
        if not target_database_url:
            raise ValueError("Remote database is not configured.")

        attempted = 0
        imported = 0
        failed = 0
        for candidate in candidates:
            if candidate.status is not CandidateStatus.APPROVED:
                continue
            attempted += 1
            try:
                self.import_candidate(candidate, database_url=target_database_url, remote_config_name=config_name)
                imported += 1
            except Exception as exc:
                failed += 1
                candidate.upload_status = UploadStatus.FAILED
                candidate.upload_error = str(exc)
                self._persist_candidate(candidate)
                self._record_import(
                    candidate=candidate,
                    import_status="failed",
                    target_question_id=None,
                    remote_config_name=config_name,
                    error_message=str(exc),
                    sql_snapshot=None,
                )
        return BatchImportSummary(attempted=attempted, imported=imported, failed=failed)

    def _resolve_database_url(self) -> str | None:
        database_url, _ = self._resolve_database_url_with_name()
        return database_url

    def _resolve_database_url_with_name(self) -> tuple[str | None, str | None]:
        if self.session is not None:
            config = RemoteDatabaseConfigService(self.session).get_active_config()
            if config is not None:
                return RemoteDatabaseConfigService(self.session).build_database_url(config), config.name
        return self.settings.oj_database_url, None

    def _persist_candidate(self, candidate: CandidateProblem) -> None:
        if self.session is None:
            return
        self.session.add(candidate)
        self.session.commit()
        self.session.refresh(candidate)

    def _record_import(
        self,
        *,
        candidate: CandidateProblem,
        import_status: str,
        target_question_id: int | None,
        remote_config_name: str | None,
        error_message: str | None,
        sql_snapshot: str | None,
    ) -> None:
        if self.session is None:
            return
        record = ImportRecord(
            candidate_id=candidate.candidate_id,
            import_status=import_status,
            target_question_id=target_question_id,
            remote_config_name=remote_config_name,
            error_message=error_message,
            sql_snapshot=sql_snapshot,
        )
        self.session.add(record)
        self.session.commit()

    @staticmethod
    def _generate_question_id() -> int:
        return 10**12 + (uuid.uuid4().int % 10**12)
