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
        schema_hint = {
            "localized_title": "两数求和",
            "localized_statement_markdown": "给定两个整数 a 和 b，请编写函数返回它们的和。",
            "difficulty": 1,
            "algorithm_tag": "数学",
            "knowledge_tags": "基础运算, 函数实现, 输入解析",
            "estimated_minutes": 5,
            "time_limit_ms": 1000,
            "space_limit_kb": 262144,
            "question_case_json": '[{"input":"1 2","output":"3"}]',
            "default_code_java": "public class Solution {\n    public static int add(int a, int b) {\n        return 0;\n    }\n}",
            "main_fuc_java": "public static void main(String[] args) throws Exception { }",
            "solution_outline": "解题思路：直接返回两个整数之和。",
            "solution_code_java": "public class SolutionReference {\n    public static int add(int a, int b) {\n        return a + b;\n    }\n}",
        }
        system_prompt = (
            "你正在为一个中文在线判题题库工具生成结构化候选题草稿。"
            "必须只返回合法 JSON，不要输出任何解释。"
            "localized_title、localized_statement_markdown、algorithm_tag、knowledge_tags、solution_outline 必须使用中文。"
            "default_code_java 必须是给用户看的函数题模板，不要直接给出正确答案。"
            "main_fuc_java 必须从标准输入读取数据并调用用户函数，严禁写死样例。"
        )
        user_prompt = (
            f"题目标题：\n{title}\n\n"
            f"题目描述：\n{statement_markdown}\n\n"
            "请返回一个 JSON 对象，并且只包含这些键：\n"
            f"{json.dumps(schema_hint, ensure_ascii=False)}"
        )
        return self._call_json(system_prompt=system_prompt, user_prompt=user_prompt)

    def generate_similar_candidate_draft(self, *, title: str, statement_markdown: str) -> dict | None:
        schema_hint = {
            "localized_title": "两数之和（巩固题）",
            "localized_statement_markdown": "请生成一题与原题知识点相同、但叙事和样例不同的中文练习题。",
            "difficulty": 1,
            "algorithm_tag": "哈希表",
            "knowledge_tags": "哈希表, 数组, 目标匹配",
            "estimated_minutes": 10,
            "time_limit_ms": 1000,
            "space_limit_kb": 262144,
            "question_case_json": '[{"input":"[1,8,11,15]\\n9","output":"[0,1]"}]',
            "default_code_java": "public class Solution {\n    public static int[] twoSum(int[] nums, int target) {\n        return new int[0];\n    }\n}",
            "main_fuc_java": "public static void main(String[] args) throws Exception { }",
            "solution_outline": "解题思路：仍然使用哈希表。",
            "solution_code_java": "public class SolutionReference {\n    public static int[] twoSum(int[] nums, int target) {\n        return new int[0];\n    }\n}",
        }
        system_prompt = (
            "你正在为中文在线判题题库生成一题类似题。"
            "必须只返回合法 JSON，不要输出任何解释。"
            "新题必须与原题知识点相同或相近，但不能只是换标题。"
            "要改变题目叙事、样例和部分细节，同时保持可判题。"
            "localized_title、localized_statement_markdown、algorithm_tag、knowledge_tags、solution_outline 必须使用中文。"
        )
        user_prompt = (
            f"原题标题：\n{title}\n\n"
            f"原题描述：\n{statement_markdown}\n\n"
            "请生成 1 道中文类似题，并返回一个 JSON 对象，只包含这些键：\n"
            f"{json.dumps(schema_hint, ensure_ascii=False)}"
        )
        return self._call_json(system_prompt=system_prompt, user_prompt=user_prompt)

    def _call_json(self, *, system_prompt: str, user_prompt: str) -> dict | None:
        if not self.enabled():
            return None
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
