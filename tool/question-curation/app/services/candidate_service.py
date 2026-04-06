from __future__ import annotations

import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.candidate import CandidateProblem, CandidateStatus, UploadStatus
from app.models.dedup_match import DedupMatch


class CandidateService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_candidate(
        self,
        *,
        title: str,
        source_type: str,
        source_platform: str,
        statement_markdown: str,
    ) -> CandidateProblem:
        candidate = CandidateProblem(
            title=title,
            slug=self._next_slug(title),
            source_type=source_type,
            source_platform=source_platform,
            statement_markdown=statement_markdown,
            status=CandidateStatus.DISCOVERED,
        )
        self.session.add(candidate)
        self.session.commit()
        self.session.refresh(candidate)
        return candidate

    def list_candidates(self) -> list[CandidateProblem]:
        return list(self.session.query(CandidateProblem).order_by(CandidateProblem.candidate_id.desc()).all())

    def get_candidate(self, candidate_id: int) -> CandidateProblem | None:
        return self.session.get(CandidateProblem, candidate_id)

    def update_candidate(self, candidate: CandidateProblem, **fields) -> CandidateProblem:
        for key, value in fields.items():
            setattr(candidate, key, value)
        self.session.add(candidate)
        self.session.commit()
        self.session.refresh(candidate)
        return candidate

    def set_status(self, candidate: CandidateProblem, status: CandidateStatus) -> CandidateProblem:
        candidate.status = status
        if status == CandidateStatus.APPROVED and candidate.upload_status == UploadStatus.NOT_READY:
            candidate.upload_status = UploadStatus.READY
        self.session.add(candidate)
        self.session.commit()
        self.session.refresh(candidate)
        return candidate

    def delete_candidates(self, candidate_ids: list[int]) -> int:
        normalized_ids = [candidate_id for candidate_id in candidate_ids if candidate_id]
        if not normalized_ids:
            return 0
        self.session.execute(delete(DedupMatch).where(DedupMatch.candidate_id.in_(normalized_ids)))
        deleted = self.session.query(CandidateProblem).filter(CandidateProblem.candidate_id.in_(normalized_ids)).delete(
            synchronize_session=False
        )
        self.session.commit()
        return int(deleted)

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return normalized or "candidate"

    def _next_slug(self, title: str) -> str:
        base_slug = self._slugify(title)
        slug = base_slug
        index = 2
        while self.session.scalar(select(CandidateProblem).where(CandidateProblem.slug == slug)) is not None:
            slug = f"{base_slug}-{index}"
            index += 1
        return slug
