from app.models.candidate import CandidateStatus
from app.models.dedup_match import DedupMatch
from app.services.candidate_service import CandidateService


def test_create_candidate_persists_defaults(session) -> None:
    service = CandidateService(session)

    candidate = service.create_candidate(
        title="Two Sum",
        source_type="manual",
        source_platform="reference",
        statement_markdown="Find two numbers.",
    )

    assert candidate.title == "Two Sum"
    assert candidate.status == CandidateStatus.DISCOVERED
    assert candidate.slug == "two-sum"


def test_delete_candidates_removes_candidates_and_dedup_matches(session) -> None:
    service = CandidateService(session)

    first = service.create_candidate(
        title="Two Sum",
        source_type="manual",
        source_platform="reference",
        statement_markdown="Problem statement",
    )
    second = service.create_candidate(
        title="Merge Intervals",
        source_type="manual",
        source_platform="reference",
        statement_markdown="Problem statement",
    )
    session.add(
        DedupMatch(
            candidate_id=first.candidate_id,
            matched_question_id=1,
            matched_title="Existing Two Sum",
            title_similarity=1.0,
            semantic_similarity=1.0,
            tag_similarity=1.0,
            io_similarity=1.0,
            overall_similarity=1.0,
            decision="probable_duplicate",
            reason="title=1.0",
        )
    )
    session.commit()

    deleted = service.delete_candidates([first.candidate_id, second.candidate_id])

    assert deleted == 2
    assert service.list_candidates() == []
    assert session.query(DedupMatch).count() == 0
