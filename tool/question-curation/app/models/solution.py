from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CandidateSolution(Base):
    __tablename__ = "candidate_solution"

    solution_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_problem.candidate_id"), nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    solution_code: Mapped[str] = mapped_column(Text, nullable=False)
    solution_outline: Mapped[str | None] = mapped_column(Text, nullable=True)
    complexity_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    correctness_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
