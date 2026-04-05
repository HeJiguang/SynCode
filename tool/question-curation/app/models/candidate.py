from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CandidateStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    MATERIAL_COLLECTED = "MATERIAL_COLLECTED"
    NORMALIZED = "NORMALIZED"
    DEDUP_CHECKED = "DEDUP_CHECKED"
    ARTIFACTS_GENERATED = "ARTIFACTS_GENERATED"
    REVIEW_READY = "REVIEW_READY"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IMPORTED = "IMPORTED"


class CandidateProblem(Base):
    __tablename__ = "candidate_problem"

    candidate_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_platform: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_problem_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[CandidateStatus] = mapped_column(
        SqlEnum(CandidateStatus),
        nullable=False,
        default=CandidateStatus.DISCOVERED,
    )
    difficulty: Mapped[int | None] = mapped_column(nullable=True)
    algorithm_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    knowledge_tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(nullable=True)
    time_limit_ms: Mapped[int | None] = mapped_column(nullable=True)
    space_limit_kb: Mapped[int | None] = mapped_column(nullable=True)
    statement_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    question_case_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_code_java: Mapped[str | None] = mapped_column(Text, nullable=True)
    main_fuc_java: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution_outline: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution_code_java: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
