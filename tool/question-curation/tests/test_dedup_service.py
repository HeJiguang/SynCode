from app.services.dedup_service import DedupService, ExistingQuestion
from app.services.candidate_service import CandidateService


def test_dedup_service_flags_high_similarity() -> None:
    service = DedupService()
    candidate = {
        "title": "Two Sum",
        "statement_markdown": "Given an array and a target, return two indices.",
        "algorithm_tag": "Hash Table",
        "knowledge_tags": ["array", "hash"],
    }
    existing = [
        ExistingQuestion(
            question_id=1,
            title="Two Sum",
            content="Given an integer array nums and an integer target, return indices.",
            algorithm_tag="Hash Table",
            knowledge_tags="array,hash",
        )
    ]

    matches = service.find_matches(candidate, existing)

    assert matches[0].overall_similarity >= 0.92
    assert matches[0].decision == "probable_duplicate"


def test_dedup_service_persists_matches_for_candidate(session) -> None:
    candidate = CandidateService(session).create_candidate(
        title="Two Sum",
        source_type="manual",
        source_platform="reference",
        statement_markdown="Given an array and a target, return two indices.",
    )
    service = DedupService(session)

    matches = service.analyze_and_store(
        candidate,
        [
            ExistingQuestion(
                question_id=1,
                title="Two Sum",
                content="Given an integer array nums and an integer target, return indices.",
                algorithm_tag="Hash Table",
                knowledge_tags="array,hash",
            )
        ],
    )

    assert len(matches) == 1
    stored = service.list_matches(candidate.candidate_id)
    assert len(stored) == 1
    assert stored[0].matched_question_id == 1
