from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def create_sqlite_engine(database_url: str):
    return create_engine(database_url, future=True)


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_sqlite_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(engine) -> None:
    _rebuild_candidate_problem_if_incompatible(engine)
    Base.metadata.create_all(engine)


def _rebuild_candidate_problem_if_incompatible(engine) -> None:
    inspector = inspect(engine)
    if "candidate_problem" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("candidate_problem")}
    required_columns = {
        "difficulty",
        "algorithm_tag",
        "knowledge_tags",
        "estimated_minutes",
        "time_limit_ms",
        "space_limit_kb",
        "question_case_json",
        "default_code_java",
        "main_fuc_java",
        "solution_outline",
        "solution_code_java",
    }
    if required_columns.issubset(existing_columns):
        return
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS import_record"))
        connection.execute(text("DROP TABLE IF EXISTS review_decision"))
        connection.execute(text("DROP TABLE IF EXISTS dedup_match"))
        connection.execute(text("DROP TABLE IF EXISTS candidate_judge_case"))
        connection.execute(text("DROP TABLE IF EXISTS candidate_solution"))
        connection.execute(text("DROP TABLE IF EXISTS source_artifact"))
        connection.execute(text("DROP TABLE IF EXISTS candidate_problem"))


def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
