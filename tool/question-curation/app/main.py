from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import models as _models  # noqa: F401
from app.config import get_settings
from app.db import create_sqlite_engine, init_db
from app.routes.web import router as web_router


def create_app() -> FastAPI:
    settings = get_settings()
    engine = create_sqlite_engine(f"sqlite:///{settings.sqlite_path}")
    init_db(engine)
    app = FastAPI(title="Question Curation Tool")
    app.state.settings = settings

    static_dir = Path("tool/question-curation/app/static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard")

    app.include_router(web_router)

    return app
