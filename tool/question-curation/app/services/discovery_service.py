from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import json
import re
from urllib.parse import urlparse

import httpx


@dataclass(slots=True)
class CodeforcesLead:
    title: str
    source_platform: str
    source_url: str
    source_problem_id: str
    difficulty: int
    tags: list[str]


class DiscoveryService:
    async def search_codeforces(self, keyword: str) -> list[CodeforcesLead]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get("https://codeforces.com/api/problemset.problems")
            response.raise_for_status()
            payload = response.json()
        return self._parse_codeforces_payload(payload, keyword=keyword)

    async def fetch_reference_material(self, url: str) -> dict[str, str]:
        lowered_url = url.lower()
        if "leetcode.com" in lowered_url:
            return await self._fetch_leetcode_reference_material(url)
        if "luogu.com.cn" in lowered_url:
            return await self._fetch_luogu_reference_material(url)

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
        if self._looks_like_block_page(html):
            raise ValueError("目标页面返回了反爬或验证页，未能获取题面正文。")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        title = self._collapse_whitespace(unescape(title_match.group(1))) if title_match else url
        return {
            "title": title,
            "statement_markdown": self.extract_reference_text(html, url=url),
            "source_url": url,
        }

    async def _fetch_leetcode_reference_material(self, url: str) -> dict[str, str]:
        slug = self._extract_leetcode_slug(url)
        payload = {
            "query": (
                "query getQuestionDetail($titleSlug: String!) { "
                "question(titleSlug: $titleSlug) { "
                "questionId title titleSlug content translatedContent difficulty "
                "sampleTestCase exampleTestcases metaData codeSnippets { lang langSlug code } "
                "} }"
            ),
            "variables": {"titleSlug": slug},
        }
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.post(
                "https://leetcode.com/graphql",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Referer": f"https://leetcode.com/problems/{slug}/",
                    "User-Agent": "Mozilla/5.0",
                },
            )
            response.raise_for_status()
            body = response.json()
        question = body.get("data", {}).get("question")
        if not question:
            raise ValueError("LeetCode GraphQL 未返回题目详情。")
        statement_markdown = self._build_leetcode_statement(question)
        return {
            "title": f"{question['title']} - 力扣（LeetCode）",
            "statement_markdown": statement_markdown,
            "source_url": url,
        }

    async def _fetch_luogu_reference_material(self, url: str) -> dict[str, str]:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            html = response.text
        payload = self._extract_luogu_context_payload(html)
        if payload is None:
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
            title = self._collapse_whitespace(unescape(title_match.group(1))) if title_match else url
            return {
                "title": title,
                "statement_markdown": self.extract_reference_text(html, url=url),
                "source_url": url,
            }
        problem = payload["data"]["problem"]
        statement_markdown = self._build_luogu_statement(problem)
        return {
            "title": f"{problem['pid']} {problem['title']} - 洛谷",
            "statement_markdown": statement_markdown,
            "source_url": url,
        }

    def _parse_codeforces_payload(self, payload: dict, *, keyword: str) -> list[CodeforcesLead]:
        normalized_keyword = keyword.strip().lower()
        problems = payload.get("result", {}).get("problems", [])
        leads: list[CodeforcesLead] = []
        for problem in problems:
            name = str(problem.get("name", "")).strip()
            if normalized_keyword and normalized_keyword not in name.lower():
                continue
            contest_id = problem.get("contestId")
            index = problem.get("index")
            if contest_id is None or index is None:
                continue
            rating = int(problem.get("rating") or 1200)
            leads.append(
                CodeforcesLead(
                    title=name,
                    source_platform="codeforces",
                    source_url=f"https://codeforces.com/problemset/problem/{contest_id}/{index}",
                    source_problem_id=f"{contest_id}{index}",
                    difficulty=self._map_codeforces_rating(rating),
                    tags=list(problem.get("tags") or []),
                )
            )
        return leads

    @staticmethod
    def seed_from_reference_url(*, title: str, source_platform: str, url: str) -> dict[str, str]:
        return {
            "title": title,
            "source_type": "reference_url",
            "source_platform": source_platform,
            "source_url": url,
            "statement_markdown": "",
        }

    def extract_reference_text(self, html: str, *, url: str = "") -> str:
        focused_html = self._platform_scoped_html(html, url)
        return self._extract_generic_text(focused_html)

    def _platform_scoped_html(self, html: str, url: str) -> str:
        lowered_url = url.lower()
        if "leetcode.com" in lowered_url:
            match = re.search(
                r'<div[^>]*data-track-load="description_content"[^>]*>(.*?)</div>',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                return match.group(1)
        if "luogu.com.cn" in lowered_url:
            match = re.search(
                r'<article[^>]*class="[^"]*main[^"]*"[^>]*>(.*?)</article>',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                return match.group(1)
        if "codeforces.com" in lowered_url:
            match = re.search(
                r'<div[^>]*class="[^"]*problem-statement[^"]*"[^>]*>(.*?)</div>\s*</div>',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                return match.group(1)
            match = re.search(
                r'<div[^>]*class="[^"]*problem-statement[^"]*"[^>]*>(.*?)</div>',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                return match.group(1)
        return html

    def _extract_generic_text(self, html: str) -> str:
        without_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        with_newlines = re.sub(
            r"</?(p|div|section|article|h1|h2|h3|h4|li|pre|br|ul|ol)[^>]*>",
            "\n",
            without_scripts,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"<[^>]+>", " ", with_newlines)
        text = unescape(text)
        lines = [self._collapse_whitespace(line) for line in text.splitlines()]
        cleaned = [line for line in lines if line]
        return "\n".join(cleaned)

    def _build_leetcode_statement(self, question: dict) -> str:
        content_html = question.get("translatedContent") or question.get("content") or ""
        description = self._extract_generic_text(content_html)
        examples = self._extract_leetcode_examples(content_html, question.get("metaData") or "")
        sections = [description]
        if examples:
            for example in examples:
                sections.append("Sample Input")
                sections.append(example["input"])
                sections.append("")
                sections.append("Sample Output")
                sections.append(example["output"])
                sections.append("")
        metadata = question.get("metaData") or ""
        if metadata:
            sections.append("Function Metadata")
            sections.append(metadata)
        return "\n".join(section for section in sections if section is not None).strip()

    def _extract_leetcode_examples(self, content_html: str, metadata_raw: str) -> list[dict[str, str]]:
        blocks = re.findall(r"<pre>(.*?)</pre>", content_html, flags=re.IGNORECASE | re.DOTALL)
        if not blocks:
            return []
        metadata = self._safe_json_loads(metadata_raw) or {}
        param_names = [item.get("name") for item in metadata.get("params", []) if item.get("name")]
        examples: list[dict[str, str]] = []
        for block in blocks:
            text = self._extract_generic_text(block)
            input_match = re.search(r"Input:\s*(.*?)(?:\n|$)", text, flags=re.IGNORECASE | re.DOTALL)
            output_match = re.search(r"Output:\s*(.*?)(?:\n|$)", text, flags=re.IGNORECASE | re.DOTALL)
            if not input_match or not output_match:
                continue
            normalized_input = self._normalize_leetcode_input(input_match.group(1).strip(), param_names)
            examples.append(
                {
                    "input": normalized_input,
                    "output": output_match.group(1).strip(),
                }
            )
        return examples

    def _normalize_leetcode_input(self, raw_input: str, param_names: list[str]) -> str:
        if not param_names or "=" not in raw_input:
            return raw_input
        values: list[str] = []
        for index, name in enumerate(param_names):
            next_name = param_names[index + 1] if index + 1 < len(param_names) else None
            if next_name:
                pattern = rf"{re.escape(name)}\s*=\s*(.*?)(?:,\s*{re.escape(next_name)}\s*=|$)"
            else:
                pattern = rf"{re.escape(name)}\s*=\s*(.*)$"
            match = re.search(pattern, raw_input)
            if not match:
                return raw_input
            values.append(match.group(1).strip().rstrip(","))
        return "\n".join(values)

    def _extract_luogu_context_payload(self, html: str) -> dict | None:
        match = re.search(r'<script id="lentille-context" type="application/json">(.*?)</script>', html, flags=re.DOTALL)
        if not match:
            return None
        return self._safe_json_loads(match.group(1))

    def _build_luogu_statement(self, problem: dict) -> str:
        contenu = problem.get("contenu") or {}
        sections: list[str] = []
        for field in ("background", "description", "inputFormat", "outputFormat", "hint"):
            value = contenu.get(field)
            if isinstance(value, str) and value.strip():
                sections.append(value.strip())
                sections.append("")
        for sample in problem.get("samples") or []:
            sample_input = sample.get("input") or ""
            sample_output = sample.get("output") or ""
            sections.append("样例输入")
            sections.append(sample_input.strip())
            sections.append("")
            sections.append("样例输出")
            sections.append(sample_output.strip())
            sections.append("")
        return "\n".join(section for section in sections if section is not None).strip()

    @staticmethod
    def _extract_leetcode_slug(url: str) -> str:
        path = urlparse(url).path.strip("/")
        parts = path.split("/")
        if "problems" in parts:
            index = parts.index("problems")
            if index + 1 < len(parts):
                return parts[index + 1]
        raise ValueError("无法从 LeetCode 链接中提取题目标识。")

    @staticmethod
    def _safe_json_loads(raw: str) -> dict | None:
        try:
            return json.loads(raw)
        except Exception:
            return None

    @staticmethod
    def _looks_like_block_page(html: str) -> bool:
        lowered = html.lower()
        return "just a moment..." in lowered or "enable javascript and cookies to continue" in lowered

    @staticmethod
    def _map_codeforces_rating(rating: int) -> int:
        if rating < 1100:
            return 1
        if rating < 1800:
            return 2
        return 3

    @staticmethod
    def _collapse_whitespace(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()
