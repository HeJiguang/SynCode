from __future__ import annotations

from sqlalchemy import create_engine, text

from app.config import Settings
from app.services.dedup_service import ExistingQuestion


class OJReader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def load_existing_questions(self) -> list[ExistingQuestion]:
        if not self.settings.oj_database_url:
            return []
        engine = create_engine(self.settings.oj_database_url, future=True)
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT question_id, title, content, algorithm_tag, knowledge_tags
                    FROM tb_question
                    """
                )
            ).mappings()
            return [
                ExistingQuestion(
                    question_id=int(row["question_id"]),
                    title=str(row["title"] or ""),
                    content=str(row["content"] or ""),
                    algorithm_tag=str(row["algorithm_tag"] or ""),
                    knowledge_tags=str(row["knowledge_tags"] or ""),
                )
                for row in rows
            ]
