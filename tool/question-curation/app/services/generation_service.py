from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.services.ai_client import AIClient


@dataclass(slots=True)
class CandidateDraft:
    difficulty: int
    algorithm_tag: str
    knowledge_tags: str
    estimated_minutes: int
    time_limit_ms: int
    space_limit_kb: int
    question_case_json: str
    default_code_java: str
    main_fuc_java: str
    solution_outline: str
    solution_code_java: str


class GenerationService:
    _TAG_RULES = [
        ("Hash Table", ("two sum", "hash", "complement", "pair sum")),
        ("Dynamic Programming", ("dp", "dynamic programming", "subsequence", "knapsack")),
        ("Graph", ("graph", "bfs", "dfs", "shortest path", "topological")),
        ("Tree", ("tree", "binary tree", "bst", "lowest common ancestor")),
        ("Binary Search", ("binary search", "sorted array", "mid")),
        ("Sorting", ("sort", "merge", "interval")),
        ("Backtracking", ("backtracking", "permutation", "combination", "subset")),
        ("Greedy", ("greedy", "maximize", "minimum number")),
    ]

    def __init__(self, ai_client: AIClient | object | None = None) -> None:
        self.ai_client = ai_client

    def generate_from_statement(self, *, title: str, statement_markdown: str) -> CandidateDraft:
        ai_draft = self._generate_with_ai(title=title, statement_markdown=statement_markdown)
        if ai_draft is not None:
            return ai_draft

        combined = f"{title}\n{statement_markdown}".lower()
        algorithm_tag = self._infer_algorithm_tag(combined)
        knowledge_tags = self._infer_knowledge_tags(algorithm_tag, combined)
        difficulty = self._infer_difficulty(combined)
        estimated_minutes = {1: 15, 2: 25, 3: 40}[difficulty]
        cases = self._extract_cases(statement_markdown)

        return CandidateDraft(
            difficulty=difficulty,
            algorithm_tag=algorithm_tag,
            knowledge_tags=", ".join(knowledge_tags),
            estimated_minutes=estimated_minutes,
            time_limit_ms=1000,
            space_limit_kb=262144,
            question_case_json=json.dumps(cases, ensure_ascii=False),
            default_code_java=self._default_code_java(),
            main_fuc_java=self._default_main_fuc_java(),
            solution_outline=self._solution_outline(algorithm_tag),
            solution_code_java=self._solution_code_java(algorithm_tag),
        )

    def _generate_with_ai(self, *, title: str, statement_markdown: str) -> CandidateDraft | None:
        if self.ai_client is None:
            return None
        try:
            payload = self.ai_client.generate_candidate_draft(title=title, statement_markdown=statement_markdown)
        except Exception:
            return None
        if not payload:
            return None
        try:
            return CandidateDraft(
                difficulty=int(payload["difficulty"]),
                algorithm_tag=str(payload["algorithm_tag"]),
                knowledge_tags=str(payload["knowledge_tags"]),
                estimated_minutes=int(payload["estimated_minutes"]),
                time_limit_ms=int(payload["time_limit_ms"]),
                space_limit_kb=int(payload["space_limit_kb"]),
                question_case_json=str(payload["question_case_json"]),
                default_code_java=str(payload["default_code_java"]),
                main_fuc_java=str(payload["main_fuc_java"]),
                solution_outline=str(payload["solution_outline"]),
                solution_code_java=str(payload["solution_code_java"]),
            )
        except Exception:
            return None

    def _infer_algorithm_tag(self, combined_text: str) -> str:
        for tag, keywords in self._TAG_RULES:
            if any(keyword in combined_text for keyword in keywords):
                return tag
        return "Algorithm"

    def _infer_knowledge_tags(self, algorithm_tag: str, combined_text: str) -> list[str]:
        tags = [algorithm_tag]
        if "array" in combined_text:
            tags.append("Array")
        if "string" in combined_text:
            tags.append("String")
        if "target" in combined_text:
            tags.append("Target Matching")
        if "index" in combined_text or "indices" in combined_text:
            tags.append("Index Mapping")
        deduped: list[str] = []
        for tag in tags:
            if tag not in deduped:
                deduped.append(tag)
        return deduped

    @staticmethod
    def _infer_difficulty(combined_text: str) -> int:
        hard_signals = ("advanced", "hard", "difficult", "large constraints", "10^5")
        easy_signals = ("easy", "basic", "intro")
        if any(signal in combined_text for signal in hard_signals):
            return 3
        if any(signal in combined_text for signal in easy_signals):
            return 1
        return 2

    def _extract_cases(self, statement_markdown: str) -> list[dict[str, str]]:
        patterns = [
            r"Sample Input\s*(?P<input>.*?)\s*Sample Output\s*(?P<output>.*?)(?=\n[A-Z][^\n]*:?\s|\Z)",
            r"Input Example\s*(?P<input>.*?)\s*Output Example\s*(?P<output>.*?)(?=\n[A-Z][^\n]*:?\s|\Z)",
            r"样例输入\s*(?P<input>.*?)\s*样例输出\s*(?P<output>.*?)(?=\n\S|\Z)",
            r"输入样例\s*(?P<input>.*?)\s*输出样例\s*(?P<output>.*?)(?=\n\S|\Z)",
        ]
        for pattern in patterns:
            matches = list(re.finditer(pattern, statement_markdown, flags=re.IGNORECASE | re.DOTALL))
            if matches:
                return [
                    {
                        "input": match.group("input").strip(),
                        "output": match.group("output").strip(),
                    }
                    for match in matches
                ]
        return [{"input": "", "output": ""}]

    @staticmethod
    def _default_code_java() -> str:
        return (
            "import java.io.*;\n"
            "import java.util.*;\n\n"
            "public class Solution {\n"
            "    public static String solve(String input) {\n"
            '        return "";\n'
            "    }\n"
            "}\n"
        )

    @staticmethod
    def _default_main_fuc_java() -> str:
        return (
            "public static void main(String[] args) throws Exception {\n"
            "    BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));\n"
            "    StringBuilder input = new StringBuilder();\n"
            "    String line;\n"
            "    while ((line = reader.readLine()) != null) {\n"
            "        input.append(line).append(\"\\n\");\n"
            "    }\n"
            "    System.out.print(solve(input.toString().trim()));\n"
            "}\n"
        )

    @staticmethod
    def _solution_outline(algorithm_tag: str) -> str:
        return (
            f"Recommended approach: {algorithm_tag}.\n"
            "Complexity: aim for O(n) or the simplest correct baseline that matches the problem constraints.\n"
            "Review focus: validate edge cases, input parsing, and output formatting."
        )

    @staticmethod
    def _solution_code_java(algorithm_tag: str) -> str:
        if algorithm_tag == "Hash Table":
            return (
                "import java.util.*;\n\n"
                "public class SolutionReference {\n"
                "    public static int[] solve(int[] nums, int target) {\n"
                "        Map<Integer, Integer> seen = new HashMap<>();\n"
                "        for (int i = 0; i < nums.length; i++) {\n"
                "            int need = target - nums[i];\n"
                "            if (seen.containsKey(need)) {\n"
                "                return new int[] {seen.get(need), i};\n"
                "            }\n"
                "            seen.put(nums[i], i);\n"
                "        }\n"
                "        return new int[] {-1, -1};\n"
                "    }\n"
                "}\n"
            )
        return (
            "public class SolutionReference {\n"
            "    public static String solve(String input) {\n"
            '        return "";\n'
            "    }\n"
            "}\n"
        )
