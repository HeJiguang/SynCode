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
            "difficulty": 2,
            "algorithm_tag": "Hash Table",
            "knowledge_tags": "array, hash",
            "estimated_minutes": 25,
            "time_limit_ms": 1000,
            "space_limit_kb": 262144,
            "question_case_json": '[{"input":"1 2","output":"3"}]',
            "default_code_java": "public class Solution {}",
            "main_fuc_java": "public static void main(String[] args) {}",
            "solution_outline": "Complexity: O(n)",
            "solution_code_java": "public class SolutionReference {}",
        }
        system_prompt = (
            "You are generating a structured candidate problem draft for an online judge curation tool. "
            "Return only valid JSON with the required keys. "
            "Be conservative. If uncertain, use simple defaults."
        )
        user_prompt = (
            f"Title:\n{title}\n\n"
            f"Statement:\n{statement_markdown}\n\n"
            f"Return JSON with exactly these keys:\n{json.dumps(schema_hint, ensure_ascii=False)}"
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
