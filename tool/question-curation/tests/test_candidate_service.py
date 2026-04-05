from app.models.candidate import CandidateStatus
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
