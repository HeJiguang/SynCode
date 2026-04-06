from app.services.generation_service import GenerationService


def test_generation_service_generates_function_style_problem_package() -> None:
    service = GenerationService()
    draft = service.generate_from_statement(
        title="两数求和",
        statement_markdown="""
给定两个整数 a 和 b，请编写函数返回它们的和。
输入描述：输入一行，包含两个整数 a 和 b，以空格分隔。
输出描述：输出一个整数，表示 a + b 的结果。
样例输入
1 2

样例输出
3
""".strip(),
    )

    assert draft.localized_title == "两数求和"
    assert "给定两个整数" in draft.localized_statement_markdown
    assert draft.difficulty == 1
    assert draft.algorithm_tag == "数学"
    assert "基础运算" in draft.knowledge_tags
    assert draft.question_case_json.startswith("[")
    assert '"output": "3"' in draft.question_case_json
    assert "public class Solution" in draft.default_code_java
    assert "public static int add(int a, int b)" in draft.default_code_java
    assert "return 0;" in draft.default_code_java
    assert "reader.readLine()" in draft.main_fuc_java
    assert "System.out.print(add(a, b));" in draft.main_fuc_java
    assert "解题思路" in draft.solution_outline
    assert "时间复杂度" in draft.solution_outline
    assert "public static int add(int a, int b)" in draft.solution_code_java
    assert "return a + b;" in draft.solution_code_java


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


def test_generation_service_builds_two_sum_function_problem_package() -> None:
    service = GenerationService()

    draft = service.generate_from_statement(
        title="Two Sum - 力扣（LeetCode）",
        statement_markdown="""
Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.

Sample Input
[2,7,11,15]
9

Sample Output
[0,1]

Function Metadata
{"name":"twoSum","params":[{"name":"nums","type":"integer[]"},{"name":"target","type":"integer"}],"return":{"type":"integer[]"}}
""".strip(),
    )

    assert any("\u4e00" <= ch <= "\u9fff" for ch in draft.localized_title)
    assert "给定" in draft.localized_statement_markdown
    assert draft.algorithm_tag == "哈希表"
    assert "数组" in draft.knowledge_tags
    assert "public static int[] twoSum(int[] nums, int target)" in draft.default_code_java
    assert "parseIntArray" in draft.main_fuc_java
    assert "System.out.print(java.util.Arrays.toString(twoSum(nums, target)));" in draft.main_fuc_java
    assert "哈希表" in draft.solution_outline
    assert "return new int[] {seen.get(need), i};" in draft.solution_code_java


def test_generation_service_uses_ai_result_when_client_available() -> None:
    class FakeClient:
        def generate_candidate_draft(self, *, title: str, statement_markdown: str):
            return {
                "localized_title": "最短路径",
                "localized_statement_markdown": "给定一张图，求最短路径。",
                "difficulty": 3,
                "algorithm_tag": "图论",
                "knowledge_tags": "图论, 广度优先搜索",
                "estimated_minutes": 45,
                "time_limit_ms": 1500,
                "space_limit_kb": 262144,
                "question_case_json": '[{"input":"1","output":"1"}]',
                "default_code_java": "public class Solution {\n    public static int shortestPath(int n) {\n        return -1;\n    }\n}",
                "main_fuc_java": "public static void main(String[] args) { Solution sol = new Solution(); int[] nums1 = {2,7,11,15}; System.out.println(sol.shortestPath(4)); }",
                "solution_outline": "这是一份图论题解草稿。",
                "solution_code_java": "public class SolutionReference {\n    public static int shortestPath(int n) {\n        return n;\n    }\n}",
            }

    service = GenerationService(ai_client=FakeClient())

    draft = service.generate_from_statement(
        title="Graph Path",
        statement_markdown="Find the shortest path.",
    )

    assert draft.localized_title == "最短路径"
    assert draft.localized_statement_markdown == "给定一张图，求最短路径。"
    assert draft.difficulty == 3
    assert draft.algorithm_tag == "图论"
    assert draft.solution_outline == "这是一份图论题解草稿。"
    assert "reader.readLine()" in draft.main_fuc_java
    assert "nums1" not in draft.main_fuc_java


def test_generation_service_normalizes_invalid_ai_main_function() -> None:
    class FakeClient:
        def generate_candidate_draft(self, *, title: str, statement_markdown: str):
            return {
                "localized_title": "两数求和",
                "localized_statement_markdown": "给定两个整数 a 和 b，请返回它们的和。",
                "difficulty": 1,
                "algorithm_tag": "数学",
                "knowledge_tags": "基础运算",
                "estimated_minutes": 5,
                "time_limit_ms": 1000,
                "space_limit_kb": 262144,
                "question_case_json": '[{"input":"1 2","output":"3"}]',
                "default_code_java": "public class Solution {\n    public static int add(int a, int b) {\n        return 0;\n    }\n}",
                "main_fuc_java": "public static void main(String[] args) { System.out.print(add(1, 2)); }",
                "solution_outline": "解题思路：直接返回两数之和。",
                "solution_code_java": "public class SolutionReference {\n    public static int add(int a, int b) {\n        return a + b;\n    }\n}",
            }

    service = GenerationService(ai_client=FakeClient())

    draft = service.generate_from_statement(
        title="两数求和",
        statement_markdown="""
给定两个整数 a 和 b，请编写函数返回它们的和。
样例输入
1 2

样例输出
3
""".strip(),
    )

    assert "reader.readLine()" in draft.main_fuc_java
    assert "System.out.print(add(a, b));" in draft.main_fuc_java
    assert "add(1, 2)" not in draft.main_fuc_java


def test_generation_service_extracts_cases_from_copied_problem_text() -> None:
    service = GenerationService()

    draft = service.generate_from_statement(
        title="两数之和",
        statement_markdown="""
给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值 target 的那两个整数，并返回它们的数组下标。

示例 1：
输入：nums = [2,7,11,15], target = 9
输出：[0,1]

示例 2：
输入：nums = [3,2,4], target = 6
输出：[1,2]
""".strip(),
    )

    assert '"input": "[2,7,11,15]\\n9"' in draft.question_case_json
    assert '"output": "[0,1]"' in draft.question_case_json
    assert '"input": "[3,2,4]\\n6"' in draft.question_case_json


def test_generation_service_generates_similar_problem_from_existing_one() -> None:
    service = GenerationService()

    draft = service.generate_similar_problem(
        title="两数之和",
        statement_markdown="""
给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值 target 的那两个整数，并返回它们的数组下标。

示例 1：
输入：nums = [2,7,11,15], target = 9
输出：[0,1]
""".strip(),
    )

    assert "巩固" in draft.localized_title or "变式" in draft.localized_title
    assert "哈希表" in draft.solution_outline
    assert '"input"' in draft.question_case_json
