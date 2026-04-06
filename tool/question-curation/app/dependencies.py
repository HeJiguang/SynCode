from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import create_session_factory


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db_session(request: Request) -> Generator[Session, None, None]:
    settings = request.app.state.settings
    session_factory = create_session_factory(f"sqlite:///{settings.sqlite_path}")
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
