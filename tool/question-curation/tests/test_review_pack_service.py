from pathlib import Path

from app.services.review_pack_service import ReviewPackService


def test_review_pack_written_to_expected_path(session, settings, candidate_factory) -> None:
    candidate = candidate_factory(session, title="Two Sum")
    service = ReviewPackService(settings)

    pack_path = service.write_review_pack(candidate)

    assert pack_path == Path(settings.review_pack_dir) / f"{candidate.candidate_id}.json"
    assert pack_path.exists()


def test_review_pack_includes_solution_draft(session, settings, candidate_factory) -> None:
    candidate = candidate_factory(
        session,
        title="Two Sum",
        statement_markdown="Given values.\n\nSample Input\n1 2\nSample Output\n3",
        default_code_java="public class Solution {}",
        main_fuc_java="public static void main(String[] args) {}",
        solution_outline="Complexity: O(n)",
        solution_code_java="public class SolutionReference {}",
    )
    service = ReviewPackService(settings)

    pack_path = service.write_review_pack(candidate)
    payload = pack_path.read_text(encoding="utf-8")

    assert "Complexity: O(n)" in payload
    assert "SolutionReference" in payload
