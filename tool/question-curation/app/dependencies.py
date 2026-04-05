from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import create_session_factory


def get_app_settings() -> Settings:
    return get_settings()


def get_db_session() -> Generator[Session, None, None]:
    settings = get_app_settings()
    session_factory = create_session_factory(f"sqlite:///{settings.sqlite_path}")
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
