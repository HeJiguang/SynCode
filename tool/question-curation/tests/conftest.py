from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import create_sqlite_engine, init_db
from app.services.candidate_service import CandidateService


@pytest.fixture
def session(tmp_path: Path) -> Session:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_sqlite_engine(database_url)
    init_db(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        review_pack_dir=tmp_path / "data" / "review_packs",
        raw_source_dir=tmp_path / "data" / "raw_sources",
        execution_dir=tmp_path / "data" / "execution",
        sqlite_path=tmp_path / "data" / "sqlite" / "question-curation.db",
    )


@pytest.fixture
def candidate_factory():
    def factory(session: Session, **overrides):
        service = CandidateService(session)
        candidate = service.create_candidate(
            title=overrides.get("title", "Candidate"),
            source_type=overrides.get("source_type", "manual"),
            source_platform=overrides.get("source_platform", "reference"),
            statement_markdown=overrides.get("statement_markdown", "Problem statement"),
        )
        for field in [
            "question_case_json",
            "default_code_java",
            "main_fuc_java",
            "solution_outline",
            "solution_code_java",
            "difficulty",
            "algorithm_tag",
            "knowledge_tags",
            "estimated_minutes",
            "time_limit_ms",
            "space_limit_kb",
        ]:
            if field in overrides:
                setattr(candidate, field, overrides[field])
        session.add(candidate)
        session.commit()
        session.refresh(candidate)
        return candidate

    return factory
