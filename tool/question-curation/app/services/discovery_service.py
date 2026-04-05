from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re

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
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        title = self._collapse_whitespace(unescape(title_match.group(1))) if title_match else url
        return {
            "title": title,
            "statement_markdown": self.extract_reference_text(html, url=url),
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
            r"</?(p|div|section|article|h1|h2|h3|h4|li|pre|br)[^>]*>",
            "\n",
            without_scripts,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"<[^>]+>", " ", with_newlines)
        text = unescape(text)
        lines = [self._collapse_whitespace(line) for line in text.splitlines()]
        cleaned = [line for line in lines if line]
        return "\n".join(cleaned)

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
