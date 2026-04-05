from __future__ import annotations

import json
from pathlib import Path

from app.config import Settings
from app.models.candidate import CandidateProblem


class ReviewPackService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def write_review_pack(self, candidate: CandidateProblem) -> Path:
        self.settings.review_pack_dir.mkdir(parents=True, exist_ok=True)
        pack_path = self.settings.review_pack_dir / f"{candidate.candidate_id}.json"
        payload = {
            "candidateId": candidate.candidate_id,
            "title": candidate.title,
            "slug": candidate.slug,
            "status": candidate.status.value,
            "source": {
                "type": candidate.source_type,
                "platform": candidate.source_platform,
                "url": candidate.source_url,
                "problemId": candidate.source_problem_id,
            },
            "statementMarkdown": candidate.statement_markdown,
            "solutionDraft": {
                "outline": candidate.solution_outline,
                "javaCode": candidate.solution_code_java,
            },
        }
        pack_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return pack_path
