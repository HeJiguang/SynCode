from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DedupMatch(Base):
    __tablename__ = "dedup_match"

    match_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_problem.candidate_id"), nullable=False)
    matched_question_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_title: Mapped[str] = mapped_column(String(255), nullable=False)
    title_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    semantic_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tag_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    io_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    decision: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
