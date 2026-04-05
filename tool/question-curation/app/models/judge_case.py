from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CandidateJudgeCase(Base):
    __tablename__ = "candidate_judge_case"

    case_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_problem.candidate_id"), nullable=False)
    case_type: Mapped[str] = mapped_column(String(32), nullable=False)
    case_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
