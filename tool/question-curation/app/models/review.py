from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ReviewDecision(Base):
    __tablename__ = "review_decision"

    review_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_problem.candidate_id"), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
