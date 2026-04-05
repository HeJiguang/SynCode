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


@dataclass(slots=True)
class JavaSignature:
    return_type: str
    method_name: str
    params: list[tuple[str, str]]
    is_static: bool


class GenerationService:
    _MATH_KEYWORDS = ("两数求和", "两数之和", "a+b", "a + b", "sum", "add", "两个整数", "两个数字")
    _TWO_SUM_ARRAY_KEYWORDS = ("two sum", "两数之和", "target", "indices", "index", "数组", "array")
    _STRING_KEYWORDS = ("reverse", "反转", "回文", "palindrome", "string", "字符串")
    _GRAPH_KEYWORDS = ("graph", "shortest path", "bfs", "dfs", "图", "最短路", "广度优先", "深度优先")
    _TREE_KEYWORDS = ("tree", "binary tree", "bst", "树", "二叉树")
    _EASY_KEYWORDS = ("easy", "简单", "基础", "入门")
    _HARD_KEYWORDS = ("hard", "困难", "10^5", "10^6", "large constraints")

    def __init__(self, ai_client: AIClient | object | None = None) -> None:
        self.ai_client = ai_client

    def generate_from_statement(self, *, title: str, statement_markdown: str) -> CandidateDraft:
        ai_draft = self._generate_with_ai(title=title, statement_markdown=statement_markdown)
        if ai_draft is not None:
            return ai_draft

        return self._build_rule_draft(title=title, statement_markdown=statement_markdown)

    def _build_rule_draft(self, *, title: str, statement_markdown: str) -> CandidateDraft:
        combined = f"{title}\n{statement_markdown}"
        normalized = combined.lower()
        signature = self._infer_signature_from_text(title=title, statement_markdown=statement_markdown)
        cases = self._extract_cases(statement_markdown)
        algorithm_tag = self._infer_algorithm_tag(normalized)
        knowledge_tags = self._infer_knowledge_tags(algorithm_tag, normalized)
        difficulty = self._infer_difficulty(normalized)
        estimated_minutes = {1: 5, 2: 20, 3: 40}[difficulty]

        default_code_java = self._render_default_code(signature)
        main_fuc_java = self._render_main_fuc(signature)
        solution_code_java = self._render_solution_code(signature)
        solution_outline = self._render_solution_outline(signature, algorithm_tag)

        return CandidateDraft(
            difficulty=difficulty,
            algorithm_tag=algorithm_tag,
            knowledge_tags=", ".join(knowledge_tags),
            estimated_minutes=estimated_minutes,
            time_limit_ms=1000,
            space_limit_kb=262144,
            question_case_json=json.dumps(cases, ensure_ascii=False),
            default_code_java=default_code_java,
            main_fuc_java=main_fuc_java,
            solution_outline=solution_outline,
            solution_code_java=solution_code_java,
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
            raw_draft = CandidateDraft(
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
        return self._normalize_ai_draft(raw_draft, title=title, statement_markdown=statement_markdown)

    def _normalize_ai_draft(
        self,
        draft: CandidateDraft,
        *,
        title: str,
        statement_markdown: str,
    ) -> CandidateDraft:
        fallback = self._build_rule_draft(title=title, statement_markdown=statement_markdown)
        signature = self._extract_signature(draft.default_code_java) or self._extract_signature(fallback.default_code_java)
        if signature is None:
            return fallback

        question_case_json = draft.question_case_json if self._is_valid_case_json(draft.question_case_json) else fallback.question_case_json

        default_code_java = draft.default_code_java if self._extract_signature(draft.default_code_java) else fallback.default_code_java
        main_fuc_java = draft.main_fuc_java
        if not self._is_valid_main_fuc(main_fuc_java, signature):
            main_fuc_java = self._render_main_fuc(signature)

        solution_code_java = draft.solution_code_java
        if signature.method_name not in solution_code_java:
            solution_code_java = self._render_solution_code(signature)

        solution_outline = draft.solution_outline.strip()
        if not self._looks_like_chinese_text(solution_outline):
            solution_outline = self._render_solution_outline(signature, draft.algorithm_tag or fallback.algorithm_tag)

        return CandidateDraft(
            difficulty=draft.difficulty,
            algorithm_tag=draft.algorithm_tag or fallback.algorithm_tag,
            knowledge_tags=draft.knowledge_tags or fallback.knowledge_tags,
            estimated_minutes=draft.estimated_minutes or fallback.estimated_minutes,
            time_limit_ms=draft.time_limit_ms or fallback.time_limit_ms,
            space_limit_kb=draft.space_limit_kb or fallback.space_limit_kb,
            question_case_json=question_case_json,
            default_code_java=default_code_java,
            main_fuc_java=main_fuc_java,
            solution_outline=solution_outline,
            solution_code_java=solution_code_java,
        )

    def _infer_algorithm_tag(self, normalized_text: str) -> str:
        if self._looks_like_array_two_sum(normalized_text):
            return "哈希表"
        if any(keyword in normalized_text for keyword in self._MATH_KEYWORDS):
            return "数学"
        if any(keyword in normalized_text for keyword in self._GRAPH_KEYWORDS):
            return "图论"
        if any(keyword in normalized_text for keyword in self._TREE_KEYWORDS):
            return "树"
        if any(keyword in normalized_text for keyword in self._STRING_KEYWORDS):
            return "字符串"
        return "基础算法"

    def _infer_knowledge_tags(self, algorithm_tag: str, normalized_text: str) -> list[str]:
        tags = [algorithm_tag]
        if algorithm_tag == "哈希表":
            tags.extend(["数组", "目标匹配", "函数实现"])
        if algorithm_tag == "数学":
            tags.extend(["基础运算", "函数实现", "输入解析"])
        if algorithm_tag == "图论":
            tags.extend(["图遍历", "建模"])
        if "数组" in normalized_text or "array" in normalized_text:
            tags.append("数组")
        if "target" in normalized_text or "目标值" in normalized_text:
            tags.append("目标匹配")
        deduped: list[str] = []
        for tag in tags:
            if tag and tag not in deduped:
                deduped.append(tag)
        return deduped

    def _infer_difficulty(self, normalized_text: str) -> int:
        if self._looks_like_array_two_sum(normalized_text):
            return 1
        if any(keyword in normalized_text for keyword in self._MATH_KEYWORDS) and (
            "两个整数" in normalized_text or "two integers" in normalized_text
        ):
            return 1
        if any(keyword in normalized_text for keyword in self._HARD_KEYWORDS):
            return 3
        if any(keyword in normalized_text for keyword in self._EASY_KEYWORDS):
            return 1
        return 2

    def _extract_cases(self, statement_markdown: str) -> list[dict[str, str]]:
        input_labels = {"sample input", "input example", "example input", "样例输入", "输入样例"}
        output_labels = {"sample output", "output example", "example output", "样例输出", "输出样例"}
        stop_labels = {
            "constraints",
            "explanation",
            "说明",
            "提示",
            "数据范围",
            "input description",
            "output description",
            "输入描述",
            "输出描述",
        }

        lines = statement_markdown.splitlines()
        cases: list[dict[str, str]] = []
        current_input: list[str] = []
        current_output: list[str] = []
        state: str | None = None

        def flush_case() -> None:
            if current_input or current_output:
                cases.append(
                    {
                        "input": "\n".join(current_input).strip(),
                        "output": "\n".join(current_output).strip(),
                    }
                )
                current_input.clear()
                current_output.clear()

        for raw_line in lines:
            label = raw_line.strip().rstrip(":：").lower()
            if label in input_labels:
                flush_case()
                state = "input"
                continue
            if label in output_labels:
                state = "output"
                continue
            if label in stop_labels:
                if state == "output":
                    flush_case()
                state = None
                continue

            if state == "input":
                current_input.append(raw_line)
            elif state == "output":
                current_output.append(raw_line)

        flush_case()
        cleaned = [case for case in cases if case["input"] or case["output"]]
        if cleaned:
            return cleaned
        if re.search(r"样例输入|Sample Input|Input Example", statement_markdown, flags=re.IGNORECASE):
            return [{"input": "", "output": ""}]
        return [{"input": "", "output": ""}]

    def _infer_signature_from_text(self, *, title: str, statement_markdown: str) -> JavaSignature:
        normalized = f"{title}\n{statement_markdown}".lower()
        if self._looks_like_array_two_sum(normalized):
            return JavaSignature(
                return_type="int[]",
                method_name="twoSum",
                params=[("int[]", "nums"), ("int", "target")],
                is_static=True,
            )
        if any(keyword in normalized for keyword in self._MATH_KEYWORDS):
            return JavaSignature(
                return_type="int",
                method_name="add",
                params=[("int", "a"), ("int", "b")],
                is_static=True,
            )
        if any(keyword in normalized for keyword in self._STRING_KEYWORDS):
            return JavaSignature(
                return_type="String",
                method_name="solve",
                params=[("String", "s")],
                is_static=True,
            )
        return JavaSignature(
            return_type="String",
            method_name="solve",
            params=[("String", "input")],
            is_static=True,
        )

    def _extract_signature(self, java_source: str) -> JavaSignature | None:
        for match in re.finditer(
            r"public\s+(?P<static>static\s+)?(?P<return>[A-Za-z_][A-Za-z0-9_\[\]]*)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<params>[^)]*)\)",
            java_source,
        ):
            method_name = match.group("name")
            if method_name == "main":
                continue
            params = self._parse_params(match.group("params"))
            if params is None:
                continue
            return JavaSignature(
                return_type=match.group("return"),
                method_name=method_name,
                params=params,
                is_static=bool(match.group("static")),
            )
        return None

    @staticmethod
    def _parse_params(raw_params: str) -> list[tuple[str, str]] | None:
        raw_params = raw_params.strip()
        if not raw_params:
            return []
        params: list[tuple[str, str]] = []
        for chunk in raw_params.split(","):
            part = chunk.strip()
            pieces = part.split()
            if len(pieces) != 2:
                return None
            params.append((pieces[0], pieces[1]))
        return params

    def _render_default_code(self, signature: JavaSignature) -> str:
        body = self._placeholder_return(signature)
        param_text = ", ".join(f"{param_type} {param_name}" for param_type, param_name in signature.params)
        return (
            "public class Solution {\n"
            f"    public static {signature.return_type} {signature.method_name}({param_text}) {{\n"
            f"        {body}\n"
            "    }\n"
            "}\n"
        )

    def _render_solution_code(self, signature: JavaSignature) -> str:
        param_text = ", ".join(f"{param_type} {param_name}" for param_type, param_name in signature.params)
        body = self._reference_return(signature)
        return (
            "public class SolutionReference {\n"
            f"    public static {signature.return_type} {signature.method_name}({param_text}) {{\n"
            f"        {body}\n"
            "    }\n"
            "}\n"
        )

    def _render_main_fuc(self, signature: JavaSignature) -> str:
        if signature.params == [("int[]", "nums"), ("int", "target")]:
            call_target = (
                f"{signature.method_name}(nums, target)"
                if signature.is_static
                else f"new Solution().{signature.method_name}(nums, target)"
            )
            return (
                "private static int[] parseIntArray(String raw) {\n"
                "    String trimmed = raw.trim();\n"
                "    if (trimmed.startsWith(\"[\") && trimmed.endsWith(\"]\")) {\n"
                "        trimmed = trimmed.substring(1, trimmed.length() - 1).trim();\n"
                "    }\n"
                "    if (trimmed.isEmpty()) {\n"
                "        return new int[0];\n"
                "    }\n"
                "    String[] parts = trimmed.split(\"\\\\s*,\\\\s*\");\n"
                "    int[] nums = new int[parts.length];\n"
                "    for (int i = 0; i < parts.length; i++) {\n"
                "        nums[i] = Integer.parseInt(parts[i].trim());\n"
                "    }\n"
                "    return nums;\n"
                "}\n\n"
                "public static void main(String[] args) throws Exception {\n"
                "    java.io.BufferedReader reader = new java.io.BufferedReader(\n"
                "        new java.io.InputStreamReader(System.in)\n"
                "    );\n"
                "    String numsLine = reader.readLine();\n"
                "    String targetLine = reader.readLine();\n"
                "    int[] nums = parseIntArray(numsLine);\n"
                "    int target = Integer.parseInt(targetLine.trim());\n"
                f"    System.out.print(java.util.Arrays.toString({call_target}));\n"
                "}\n"
            )
        if signature.params == [("int", "a"), ("int", "b")]:
            call_target = f"{signature.method_name}(a, b)" if signature.is_static else f"new Solution().{signature.method_name}(a, b)"
            return (
                "public static void main(String[] args) throws Exception {\n"
                "    java.io.BufferedReader reader = new java.io.BufferedReader(\n"
                "        new java.io.InputStreamReader(System.in)\n"
                "    );\n"
                "    String[] parts = reader.readLine().trim().split(\"\\\\s+\");\n"
                "    int a = Integer.parseInt(parts[0]);\n"
                "    int b = Integer.parseInt(parts[1]);\n"
                f"    System.out.print({call_target});\n"
                "}\n"
            )
        if signature.params == [("int", "n")]:
            call_target = f"{signature.method_name}(n)" if signature.is_static else f"new Solution().{signature.method_name}(n)"
            return (
                "public static void main(String[] args) throws Exception {\n"
                "    java.io.BufferedReader reader = new java.io.BufferedReader(\n"
                "        new java.io.InputStreamReader(System.in)\n"
                "    );\n"
                "    int n = Integer.parseInt(reader.readLine().trim());\n"
                f"    System.out.print({call_target});\n"
                "}\n"
            )
        if signature.params == [("String", "s")]:
            call_target = f'{signature.method_name}(s)' if signature.is_static else f'new Solution().{signature.method_name}(s)'
            return (
                "public static void main(String[] args) throws Exception {\n"
                "    java.io.BufferedReader reader = new java.io.BufferedReader(\n"
                "        new java.io.InputStreamReader(System.in)\n"
                "    );\n"
                "    String s = reader.readLine();\n"
                f"    System.out.print({call_target});\n"
                "}\n"
            )
        call_target = f'{signature.method_name}(input.toString().trim())' if signature.is_static else f'new Solution().{signature.method_name}(input.toString().trim())'
        return (
            "public static void main(String[] args) throws Exception {\n"
            "    java.io.BufferedReader reader = new java.io.BufferedReader(\n"
            "        new java.io.InputStreamReader(System.in)\n"
            "    );\n"
            "    StringBuilder input = new StringBuilder();\n"
            "    String line;\n"
            "    while ((line = reader.readLine()) != null) {\n"
            "        input.append(line).append(\"\\n\");\n"
            "    }\n"
            f"    System.out.print({call_target});\n"
            "}\n"
        )

    def _render_solution_outline(self, signature: JavaSignature, algorithm_tag: str) -> str:
        if signature.method_name == "twoSum" and signature.params == [("int[]", "nums"), ("int", "target")]:
            return (
                "解题思路：使用哈希表记录已经遍历过的数字及其下标。\n"
                "遍历数组时，先计算 target - nums[i]，如果补数已经出现过，就直接返回这两个下标。\n"
                "否则把当前数字和下标放入哈希表继续遍历。\n"
                "时间复杂度：O(n)。\n"
                "空间复杂度：O(n)。"
            )
        if signature.method_name == "add" and signature.params == [("int", "a"), ("int", "b")]:
            return (
                "解题思路：这道题只需要返回两个整数之和。\n"
                "先读取两个整数参数 a 和 b，再调用用户实现的 add(a, b)。\n"
                "时间复杂度：O(1)。\n"
                "空间复杂度：O(1)。"
            )
        return (
            f"解题思路：优先按照{algorithm_tag}的基础做法实现函数逻辑。\n"
            "平台会负责读取输入并调用你需要实现的方法。\n"
            "时间复杂度：请根据题目要求选择最直接且正确的实现。\n"
            "空间复杂度：尽量保持额外空间开销可控。"
        )

    @staticmethod
    def _placeholder_return(signature: JavaSignature) -> str:
        if signature.return_type == "int":
            return "return 0;"
        if signature.return_type == "long":
            return "return 0L;"
        if signature.return_type == "boolean":
            return "return false;"
        if signature.return_type == "String":
            return 'return "";'
        if signature.return_type.endswith("[]"):
            return f"return new {signature.return_type[:-2]}[0];"
        return "return null;"

    @staticmethod
    def _reference_return(signature: JavaSignature) -> str:
        if signature.method_name == "twoSum" and signature.params == [("int[]", "nums"), ("int", "target")]:
            return (
                "java.util.Map<Integer, Integer> seen = new java.util.HashMap<>();\n"
                "        for (int i = 0; i < nums.length; i++) {\n"
                "            int need = target - nums[i];\n"
                "            if (seen.containsKey(need)) {\n"
                "                return new int[] {seen.get(need), i};\n"
                "            }\n"
                "            seen.put(nums[i], i);\n"
                "        }\n"
                "        return new int[0];"
            )
        if signature.method_name == "add" and signature.params == [("int", "a"), ("int", "b")]:
            return "return a + b;"
        if signature.return_type == "String":
            param_name = signature.params[0][1] if signature.params else "input"
            return f"return {param_name};"
        return GenerationService._placeholder_return(signature)

    @staticmethod
    def _is_valid_case_json(question_case_json: str) -> bool:
        try:
            payload = json.loads(question_case_json)
        except Exception:
            return False
        return isinstance(payload, list) and all(isinstance(item, dict) for item in payload)

    def _is_valid_main_fuc(self, main_fuc_java: str, signature: JavaSignature) -> bool:
        if "System.in" not in main_fuc_java and "reader.readLine()" not in main_fuc_java and "Scanner" not in main_fuc_java:
            return False
        if re.search(r"\{\s*\d+(?:\s*,\s*\d+)+\s*\}", main_fuc_java):
            return False
        if re.search(rf"{re.escape(signature.method_name)}\s*\(\s*\d", main_fuc_java):
            return False
        if signature.method_name not in main_fuc_java:
            return False
        return True

    @staticmethod
    def _looks_like_chinese_text(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text))

    def _looks_like_array_two_sum(self, normalized_text: str) -> bool:
        return (
            any(keyword in normalized_text for keyword in ("two sum", "两数之和"))
            and any(keyword in normalized_text for keyword in ("array", "数组", "nums"))
            and any(keyword in normalized_text for keyword in ("target", "indices", "index", "下标"))
        )
