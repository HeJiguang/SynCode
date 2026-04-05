from app.services.generation_service import GenerationService


def test_generation_service_derives_cases_and_java_artifacts() -> None:
    service = GenerationService()
    draft = service.generate_from_statement(
        title="Two Sum",
        statement_markdown="""
Given an array of integers and a target value, return the indexes of the two numbers.

Sample Input
4
2 7 11 15
9

Sample Output
0 1
""".strip(),
    )

    assert draft.difficulty == 2
    assert "Hash Table" in draft.algorithm_tag
    assert draft.question_case_json.startswith("[")
    assert '"output": "0 1"' in draft.question_case_json
    assert "public class Solution" in draft.default_code_java
    assert "public static void main" in draft.main_fuc_java
    assert "Complexity" in draft.solution_outline
    assert "public static" in draft.solution_code_java


def test_generation_service_extracts_multiple_samples() -> None:
    service = GenerationService()

    draft = service.generate_from_statement(
        title="A Plus B",
        statement_markdown="""
Compute the sum.

Sample Input
1 2
Sample Output
3

Sample Input
5 7
Sample Output
12
""".strip(),
    )

    assert draft.question_case_json.count('"input"') == 2


def test_generation_service_uses_ai_result_when_client_available() -> None:
    class FakeClient:
        def generate_candidate_draft(self, *, title: str, statement_markdown: str):
            return {
                "difficulty": 3,
                "algorithm_tag": "Graph",
                "knowledge_tags": "graph, bfs",
                "estimated_minutes": 45,
                "time_limit_ms": 1500,
                "space_limit_kb": 262144,
                "question_case_json": '[{"input":"1","output":"1"}]',
                "default_code_java": "public class Solution {}",
                "main_fuc_java": "public static void main(String[] args) {}",
                "solution_outline": "Complexity: O(V+E)",
                "solution_code_java": "public class SolutionReference {}",
            }

    service = GenerationService(ai_client=FakeClient())

    draft = service.generate_from_statement(
        title="Graph Path",
        statement_markdown="Find the shortest path.",
    )

    assert draft.difficulty == 3
    assert draft.algorithm_tag == "Graph"
    assert draft.solution_outline == "Complexity: O(V+E)"
