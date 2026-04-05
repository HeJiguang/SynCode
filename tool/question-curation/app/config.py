from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(slots=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8010
    data_dir: Path = Path("tool/question-curation/data")
    review_pack_dir: Path = Path("tool/question-curation/data/review_packs")
    raw_source_dir: Path = Path("tool/question-curation/data/raw_sources")
    execution_dir: Path = Path("tool/question-curation/data/execution")
    sqlite_path: Path = Path("tool/question-curation/data/sqlite/question-curation.db")
    oj_database_url: str | None = None
    import_create_by: int = 1
    llm_enabled: bool = False
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None


def get_settings() -> Settings:
    settings = Settings(
        host=os.getenv("QUESTION_CURATION_HOST", "127.0.0.1"),
        port=int(os.getenv("QUESTION_CURATION_PORT", "8010")),
        data_dir=Path(os.getenv("QUESTION_CURATION_DATA_DIR", "tool/question-curation/data")),
        review_pack_dir=Path(os.getenv("QUESTION_CURATION_REVIEW_PACK_DIR", "tool/question-curation/data/review_packs")),
        raw_source_dir=Path(os.getenv("QUESTION_CURATION_RAW_SOURCE_DIR", "tool/question-curation/data/raw_sources")),
        execution_dir=Path(os.getenv("QUESTION_CURATION_EXECUTION_DIR", "tool/question-curation/data/execution")),
        sqlite_path=Path(os.getenv("QUESTION_CURATION_SQLITE_PATH", "tool/question-curation/data/sqlite/question-curation.db")),
        oj_database_url=os.getenv("QUESTION_CURATION_OJ_DATABASE_URL"),
        import_create_by=int(os.getenv("QUESTION_CURATION_IMPORT_CREATE_BY", "1")),
        llm_enabled=os.getenv("QUESTION_CURATION_LLM_ENABLED", "false").lower() == "true",
        llm_base_url=os.getenv("QUESTION_CURATION_LLM_BASE_URL"),
        llm_api_key=os.getenv("QUESTION_CURATION_LLM_API_KEY"),
        llm_model=os.getenv("QUESTION_CURATION_LLM_MODEL"),
    )
    settings.review_pack_dir.mkdir(parents=True, exist_ok=True)
    settings.raw_source_dir.mkdir(parents=True, exist_ok=True)
    settings.execution_dir.mkdir(parents=True, exist_ok=True)
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
