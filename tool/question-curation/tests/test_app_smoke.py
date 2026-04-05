from fastapi.testclient import TestClient

from app.main import create_app
from app.services.discovery_service import DiscoveryService


def test_app_root_redirects_to_dashboard() -> None:
    client = TestClient(create_app())
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard"


def test_dashboard_page_renders_heading() -> None:
    client = TestClient(create_app())
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "题库补充工作台" in response.text


def test_database_settings_page_renders() -> None:
    client = TestClient(create_app())
    response = client.get("/settings/database")

    assert response.status_code == 200
    assert "远端数据库配置" in response.text
    assert "测试连接" in response.text


def test_save_database_settings_renders_success_message() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/settings/database/save",
        data={
            "host": "127.0.0.1",
            "port": "3306",
            "database_name": "onlineoj",
            "username": "root",
            "password": "secret",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "配置已保存到本地 SQLite" in response.text
    assert "onlineoj" in response.text


def test_create_candidate_form_redirects_to_detail() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/candidates",
        data={
            "title": "Two Sum",
            "source_type": "manual",
            "source_platform": "reference",
            "statement_markdown": "Problem statement",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/candidates/")


def test_generate_draft_updates_candidate_fields() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/candidates",
        data={
            "title": "Two Sum",
            "source_type": "manual",
            "source_platform": "reference",
            "statement_markdown": """
Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.

Sample Input
[2,7,11,15]
9

Sample Output
[0,1]
""".strip(),
        },
        follow_redirects=False,
    )
    detail_path = create_response.headers["location"]

    generate_response = client.post(f"{detail_path}/generate", follow_redirects=True)

    assert generate_response.status_code == 200
    assert "public class Solution" in generate_response.text
    assert "twoSum" in generate_response.text
    assert "main" in generate_response.text


def test_discover_page_renders() -> None:
    client = TestClient(create_app())
    response = client.get("/discover")

    assert response.status_code == 200
    assert "导入题目" in response.text


def test_fetch_reference_url_creates_candidate(monkeypatch) -> None:
    async def fake_fetch(self, url: str):
        return {
            "title": "Fetched Two Sum",
            "statement_markdown": "Given an array and a target.\n\nSample Input\n[2,7,11,15]\n9\n\nSample Output\n[0,1]",
            "source_url": url,
        }

    monkeypatch.setattr(DiscoveryService, "fetch_reference_material", fake_fetch)
    client = TestClient(create_app())

    response = client.post(
        "/discover/fetch",
        data={
            "source_platform": "leetcode",
            "source_url": "https://leetcode.com/problems/two-sum/",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    detail_path = response.headers["location"]
    assert detail_path.startswith("/candidates/")

    detail_response = client.get(detail_path)
    assert "public class Solution" in detail_response.text
    assert "候选题" in detail_response.text


def test_batch_import_urls_creates_multiple_candidates(monkeypatch) -> None:
    async def fake_fetch(self, url: str):
        slug = url.rstrip("/").split("/")[-1]
        return {
            "title": f"Fetched {slug}",
            "statement_markdown": "Given values.\n\nSample Input\n1 2\n\nSample Output\n3",
            "source_url": url,
        }

    monkeypatch.setattr(DiscoveryService, "fetch_reference_material", fake_fetch)
    client = TestClient(create_app())

    response = client.post(
        "/discover/batch",
        data={
            "source_platform": "leetcode",
            "urls_text": "\n".join(
                [
                    "https://leetcode.com/problems/two-sum/",
                    "https://leetcode.com/problems/merge-intervals/",
                ]
            ),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Fetched two-sum" in response.text
    assert "Fetched merge-intervals" in response.text
    assert "候选题列表" in response.text or "候选题" in response.text


def test_run_java_draft_renders_execution_result() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/candidates",
        data={
            "title": "Echo",
            "source_type": "manual",
            "source_platform": "reference",
            "statement_markdown": "Sample Input\nhello\nSample Output\nhello",
        },
        follow_redirects=False,
    )
    detail_path = create_response.headers["location"]
    candidate_id = detail_path.rstrip("/").split("/")[-1]
    client.post(
        f"/candidates/{candidate_id}/save",
        data={
            "title": "Echo",
            "difficulty": "1",
            "algorithm_tag": "字符串",
            "knowledge_tags": "字符串",
            "estimated_minutes": "10",
            "time_limit_ms": "1000",
            "space_limit_kb": "262144",
            "statement_markdown": "Sample Input\nhello\nSample Output\nhello",
            "question_case_json": '[{"input":"hello","output":"hello"}]',
            "default_code_java": "public class Solution {\n    public static String solve(String input) {\n        return input;\n    }\n}",
            "main_fuc_java": "public static void main(String[] args) throws Exception {\n    java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.InputStreamReader(System.in));\n    StringBuilder input = new StringBuilder();\n    String line;\n    while ((line = reader.readLine()) != null) {\n        input.append(line);\n    }\n    System.out.print(solve(input.toString()));\n}",
            "solution_outline": "解题思路：直接返回输入字符串。",
            "solution_code_java": "public class SolutionReference {\n    public static String solve(String input) {\n        return input;\n    }\n}",
        },
        follow_redirects=False,
    )

    response = client.post(f"/candidates/{candidate_id}/run-java", follow_redirects=True)

    assert response.status_code == 200
    assert "hello" in response.text
