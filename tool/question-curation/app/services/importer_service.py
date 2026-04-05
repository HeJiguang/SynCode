from __future__ import annotations

import time
import uuid

from sqlalchemy import create_engine, text

from app.config import Settings
from app.models.candidate import CandidateProblem, CandidateStatus
from app.schemas.import_preview import ImportPreview


class ImporterService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_preview(self, candidate: CandidateProblem) -> ImportPreview:
        return ImportPreview(
            title=candidate.title,
            content=candidate.statement_markdown,
            question_case=candidate.question_case_json or "[]",
            default_code=candidate.default_code_java or "",
            main_fuc=candidate.main_fuc_java or "",
        )

    def import_candidate(self, candidate: CandidateProblem) -> dict[str, str]:
        if candidate.status is not CandidateStatus.APPROVED:
            raise ValueError("Candidate must be approved before import.")
        if not self.settings.oj_database_url:
            raise ValueError("QUESTION_CURATION_OJ_DATABASE_URL is not configured.")

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
        engine = create_engine(self.settings.oj_database_url, future=True)
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
        return {"status": "imported", "question_id": str(question_id)}

    @staticmethod
    def _generate_question_id() -> int:
        return 10**12 + (uuid.uuid4().int % 10**12)
