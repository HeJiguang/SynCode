from sqlalchemy import create_engine, text

from app.models.candidate import CandidateStatus, UploadStatus
from app.services.importer_service import ImporterService
from app.services.remote_db_config_service import RemoteDatabaseConfigService
import pytest


def test_import_preview_maps_candidate_fields(candidate_factory, session, settings) -> None:
    candidate = candidate_factory(
        session,
        title="Two Sum",
        statement_markdown="Problem statement",
        question_case_json='[{"input":"1 2","output":"3"}]',
        default_code_java="public class Solution {}",
        main_fuc_java="public static void main(String[] args) {}",
    )
    service = ImporterService(settings)

    preview = service.build_preview(candidate)

    assert preview.title == "Two Sum"
    assert preview.content == "Problem statement"
    assert preview.question_case == '[{"input":"1 2","output":"3"}]'


def test_importer_rejects_unapproved_candidate(candidate_factory, session, settings) -> None:
    candidate = candidate_factory(session, title="Two Sum")
    service = ImporterService(settings)

    with pytest.raises(ValueError):
        service.import_candidate(candidate)


def test_import_candidate_inserts_row_when_approved(candidate_factory, session, settings, tmp_path) -> None:
    target_db = tmp_path / "target.db"
    engine = create_engine(f"sqlite:///{target_db}", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE tb_question (
                    question_id BIGINT PRIMARY KEY,
                    title TEXT NOT NULL,
                    difficulty INTEGER,
                    algorithm_tag TEXT,
                    knowledge_tags TEXT,
                    estimated_minutes INTEGER,
                    training_enabled INTEGER,
                    time_limit BIGINT,
                    space_limit BIGINT,
                    content TEXT,
                    question_case TEXT,
                    default_code TEXT,
                    main_fuc TEXT,
                    create_by BIGINT,
                    create_time TEXT
                )
                """
            )
        )

    settings.oj_database_url = f"sqlite:///{target_db}"
    candidate = candidate_factory(
        session,
        title="Two Sum",
        statement_markdown="Problem statement",
        question_case_json='[{"input":"1 2","output":"3"}]',
        default_code_java="public class Solution {}",
        main_fuc_java="public static void main(String[] args) {}",
        difficulty=1,
        algorithm_tag="Hash Table",
        knowledge_tags="array,hash",
        estimated_minutes=15,
        time_limit_ms=1000,
        space_limit_kb=262144,
    )
    candidate.status = CandidateStatus.APPROVED
    session.add(candidate)
    session.commit()
    service = ImporterService(settings)

    result = service.import_candidate(candidate)

    assert result["status"] == "imported"
    with engine.connect() as conn:
        row = conn.execute(text("SELECT title, content FROM tb_question")).mappings().one()
    assert row["title"] == "Two Sum"
    assert row["content"] == "Problem statement"


def test_batch_import_approved_candidates_uses_saved_remote_config(candidate_factory, session, settings, tmp_path) -> None:
    target_db = tmp_path / "batch-target.db"
    engine = create_engine(f"sqlite:///{target_db}", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE tb_question (
                    question_id BIGINT PRIMARY KEY,
                    title TEXT NOT NULL,
                    difficulty INTEGER,
                    algorithm_tag TEXT,
                    knowledge_tags TEXT,
                    estimated_minutes INTEGER,
                    training_enabled INTEGER,
                    time_limit BIGINT,
                    space_limit BIGINT,
                    content TEXT,
                    question_case TEXT,
                    default_code TEXT,
                    main_fuc TEXT,
                    create_by BIGINT,
                    create_time TEXT
                )
                """
            )
        )

    RemoteDatabaseConfigService(session).save_active_config(
        host="localhost",
        port=3306,
        database_name=str(target_db),
        username="tester",
        password="pw",
        dialect="sqlite",
        charset="utf8mb4",
    )
    candidate = candidate_factory(
        session,
        title="Two Sum",
        statement_markdown="Problem statement",
        question_case_json='[{"input":"1 2","output":"3"}]',
        default_code_java="public class Solution {}",
        main_fuc_java="public static void main(String[] args) {}",
        difficulty=1,
        algorithm_tag="Hash Table",
        knowledge_tags="array,hash",
        estimated_minutes=15,
        time_limit_ms=1000,
        space_limit_kb=262144,
    )
    candidate.status = CandidateStatus.APPROVED
    candidate.upload_status = UploadStatus.READY
    session.add(candidate)
    session.commit()

    service = ImporterService(settings, session=session)
    summary = service.batch_import_approved_candidates([candidate])

    assert summary.attempted == 1
    assert summary.imported == 1
    assert summary.failed == 0
    session.refresh(candidate)
    assert candidate.upload_status == UploadStatus.UPLOADED
