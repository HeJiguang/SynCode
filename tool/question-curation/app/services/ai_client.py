from __future__ import annotations

import json

import httpx

from app.config import Settings


class AIClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def enabled(self) -> bool:
        return bool(
            self.settings.llm_enabled
            and self.settings.llm_base_url
            and self.settings.llm_api_key
            and self.settings.llm_model
        )

    def generate_candidate_draft(self, *, title: str, statement_markdown: str) -> dict | None:
        if not self.enabled():
            return None

        schema_hint = {
            "difficulty": 1,
            "algorithm_tag": "数学",
            "knowledge_tags": "基础运算, 函数实现, 输入解析",
            "estimated_minutes": 5,
            "time_limit_ms": 1000,
            "space_limit_kb": 262144,
            "question_case_json": '[{"input":"1 2","output":"3"}]',
            "default_code_java": "public class Solution {\n    public static int add(int a, int b) {\n        return 0;\n    }\n}",
            "main_fuc_java": (
                "public static void main(String[] args) throws Exception {\n"
                "    java.io.BufferedReader reader = new java.io.BufferedReader(\n"
                "        new java.io.InputStreamReader(System.in)\n"
                "    );\n"
                "    String[] parts = reader.readLine().trim().split(\"\\\\s+\");\n"
                "    int a = Integer.parseInt(parts[0]);\n"
                "    int b = Integer.parseInt(parts[1]);\n"
                "    System.out.print(add(a, b));\n"
                "}"
            ),
            "solution_outline": "解题思路：直接返回两个整数之和。时间复杂度 O(1)，空间复杂度 O(1)。",
            "solution_code_java": "public class SolutionReference {\n    public static int add(int a, int b) {\n        return a + b;\n    }\n}",
        }
        system_prompt = (
            "你正在为一个在线判题题库工具生成结构化候选题草稿。"
            "必须只返回合法 JSON，不要输出任何解释。"
            "这是一个中文为主的系统，algorithm_tag、knowledge_tags、solution_outline 应优先使用中文。"
            "default_code_java 必须是给用户看的函数题模板：只保留 Solution 类和待实现函数，不要直接给出正确答案。"
            "main_fuc_java 是平台内部包装代码，必须从标准输入读取数据、解析参数、调用 default_code_java 中的同名函数、输出结果。"
            "main_fuc_java 严禁硬编码样例、严禁出现 add(1, 2) 这类固定参数调用、严禁直接构造示例数组。"
            "question_case_json 必须是 JSON 字符串，里面的输入格式必须和 main_fuc_java 的解析逻辑一致。"
            "solution_outline 必须是中文。"
            "如果无法稳定推断复杂函数签名，请使用最简单且可运行的函数题模板。"
        )
        user_prompt = (
            f"题目标题：\n{title}\n\n"
            f"题目描述：\n{statement_markdown}\n\n"
            "请根据这道题返回一个 JSON 对象，且必须包含且只包含下面这些键：\n"
            f"{json.dumps(schema_hint, ensure_ascii=False)}\n\n"
            "要求：\n"
            "1. default_code_java 和 main_fuc_java 必须完全配套。\n"
            "2. 用户体验要像 LeetCode：用户只实现函数，不写 main。\n"
            "3. main_fuc_java 要适配当前判题机：读取 stdin，调用函数，输出结果。\n"
            "4. 如果题目是类似两数求和这种简单函数题，优先生成清晰的函数签名，而不是 solve(String input) 这种笼统模板。"
        )
        response = httpx.post(
            f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.llm_model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=45.0,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if not content:
            return None
        return json.loads(content)
