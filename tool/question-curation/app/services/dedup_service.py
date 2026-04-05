from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.candidate import CandidateProblem
from app.models.dedup_match import DedupMatch

@dataclass(slots=True)
class ExistingQuestion:
    question_id: int
    title: str
    content: str
    algorithm_tag: str | None = None
    knowledge_tags: str | None = None


@dataclass(slots=True)
class DedupResult:
    question_id: int
    title: str
    title_similarity: float
    semantic_similarity: float
    tag_similarity: float
    io_similarity: float
    overall_similarity: float
    decision: str
    reason: str


class DedupService:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def find_matches(self, candidate: dict, existing_questions: list[ExistingQuestion]) -> list[DedupResult]:
        results: list[DedupResult] = []
        candidate_title = candidate.get("title", "")
        candidate_statement = candidate.get("statement_markdown", "")
        candidate_tags = self._normalize_tags(candidate.get("knowledge_tags", []))
        candidate_algorithm = (candidate.get("algorithm_tag") or "").strip().lower()

        for existing in existing_questions:
            title_similarity = self._ratio(candidate_title, existing.title)
            semantic_similarity = self._ratio(candidate_statement, existing.content)
            existing_tags = self._normalize_tags(existing.knowledge_tags or "")
            tag_similarity = self._tag_similarity(candidate_tags, existing_tags, candidate_algorithm, existing.algorithm_tag or "")
            io_similarity = 0.0
            overall_similarity = (
                (title_similarity * 0.45)
                + (semantic_similarity * 0.35)
                + (tag_similarity * 0.2)
            )
            decision = self._decision_for(overall_similarity)
            reason = f"title={title_similarity:.2f}, semantic={semantic_similarity:.2f}, tag={tag_similarity:.2f}"
            results.append(
                DedupResult(
                    question_id=existing.question_id,
                    title=existing.title,
                    title_similarity=title_similarity,
                    semantic_similarity=semantic_similarity,
                    tag_similarity=tag_similarity,
                    io_similarity=io_similarity,
                    overall_similarity=overall_similarity,
                    decision=decision,
                    reason=reason,
                )
            )

        return sorted(results, key=lambda item: item.overall_similarity, reverse=True)

    def analyze_and_store(
        self,
        candidate: CandidateProblem,
        existing_questions: list[ExistingQuestion],
    ) -> list[DedupMatch]:
        if self.session is None:
            raise ValueError("DedupService requires a session to persist matches.")
        matches = self.find_matches(
            {
                "title": candidate.title,
                "statement_markdown": candidate.statement_markdown,
                "algorithm_tag": candidate.algorithm_tag,
                "knowledge_tags": candidate.knowledge_tags or "",
            },
            existing_questions,
        )
        self.session.execute(delete(DedupMatch).where(DedupMatch.candidate_id == candidate.candidate_id))
        persisted: list[DedupMatch] = []
        for match in matches:
            record = DedupMatch(
                candidate_id=candidate.candidate_id,
                matched_question_id=match.question_id,
                matched_title=match.title,
                title_similarity=match.title_similarity,
                semantic_similarity=match.semantic_similarity,
                tag_similarity=match.tag_similarity,
                io_similarity=match.io_similarity,
                overall_similarity=match.overall_similarity,
                decision=match.decision,
                reason=match.reason,
            )
            self.session.add(record)
            persisted.append(record)
        self.session.commit()
        for record in persisted:
            self.session.refresh(record)
        return persisted

    def list_matches(self, candidate_id: int) -> list[DedupMatch]:
        if self.session is None:
            raise ValueError("DedupService requires a session to list matches.")
        return list(
            self.session.scalars(
                select(DedupMatch)
                .where(DedupMatch.candidate_id == candidate_id)
                .order_by(DedupMatch.overall_similarity.desc())
            )
        )

    @staticmethod
    def _ratio(left: str, right: str) -> float:
        return SequenceMatcher(None, left.strip().lower(), right.strip().lower()).ratio()

    @staticmethod
    def _normalize_tags(tags: list[str] | str) -> set[str]:
        if isinstance(tags, str):
            raw_tags = [item.strip().lower() for item in tags.replace(";", ",").split(",")]
        else:
            raw_tags = [item.strip().lower() for item in tags]
        return {item for item in raw_tags if item}

    def _tag_similarity(
        self,
        candidate_tags: set[str],
        existing_tags: set[str],
        candidate_algorithm: str,
        existing_algorithm: str,
    ) -> float:
        overlap = 0.0
        if candidate_tags or existing_tags:
            union = candidate_tags | existing_tags
            if union:
                overlap = len(candidate_tags & existing_tags) / len(union)
        algorithm_bonus = 0.3 if candidate_algorithm and candidate_algorithm == existing_algorithm.strip().lower() else 0.0
        return min(1.0, overlap + algorithm_bonus)

    @staticmethod
    def _decision_for(score: float) -> str:
        if score >= 0.92:
            return "probable_duplicate"
        if score >= 0.75:
            return "similar_problem"
        return "likely_distinct"
