"""Bounded, read-only access to the current user's OJ learning data."""

from dataclasses import dataclass, field
from typing import Any

import httpx


class LearningToolError(RuntimeError):
    pass


@dataclass
class LearningToolContext:
    profile: dict[str, int] | None = None
    submissions: dict[str, Any] | None = None
    questions: list[dict[str, Any]] = field(default_factory=list)
    calls: list[dict[str, str]] = field(default_factory=list)

    def prompt_data(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "current_question_submissions": self.submissions,
            "candidate_questions": self.questions,
        }


class LearningToolGateway:
    """Calls three fixed backend endpoints with the authenticated user's token.

    Tool arguments are selected by application code, never by model output. The
    token is kept out of Run snapshots, artifacts and LLM prompts.
    """

    def __init__(self, base_url: str, authorization: str, *, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.authorization = authorization
        self.client = client

    def collect(self, *, question_id: str | None, include_candidates: bool) -> LearningToolContext:
        context = LearningToolContext()
        self._collect_one(context, "learning_profile.get_relevant", self._profile)
        if question_id and question_id.isdecimal():
            self._collect_one(context, "submission.get_summary", lambda: self._submissions(question_id))
        if include_candidates:
            self._collect_one(context, "problem.search", self._questions)
        return context

    def submission_accepted_since(self, question_id: str, since: str) -> bool:
        if not question_id.isdecimal():
            return False
        rows = self._get("/friend/user/question/submission/list", {"questionId": question_id})
        if not isinstance(rows, list):
            raise LearningToolError("提交记录格式无效。")
        from datetime import datetime, timezone

        threshold = datetime.fromisoformat(since.replace("Z", "+00:00"))
        if threshold.tzinfo is None:
            threshold = threshold.replace(tzinfo=timezone.utc)
        for row in rows:
            if not isinstance(row, dict) or row.get("pass") != 1:
                continue
            raw_time = row.get("createTime") or row.get("updateTime")
            if not isinstance(raw_time, str):
                continue
            submitted = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            if submitted.tzinfo is None:
                # Java's LocalDateTime is emitted without an offset. The backend
                # and agent use the same deployment clock; allow a small margin.
                submitted = submitted.replace(tzinfo=timezone.utc)
            if submitted >= threshold:
                return True
        return False

    def _collect_one(self, context: LearningToolContext, name: str, operation) -> None:
        try:
            value = operation()
            if name == "learning_profile.get_relevant":
                context.profile = value
            elif name == "submission.get_summary":
                context.submissions = value
            else:
                context.questions = value
            context.calls.append({"tool_name": name, "status": "SUCCEEDED"})
        except (httpx.HTTPError, ValueError, LearningToolError) as exc:
            context.calls.append({"tool_name": name, "status": "FAILED", "reason": str(exc)[:180]})

    def _profile(self) -> dict[str, int]:
        data = self._get("/friend/user/dashboard/summary")
        if not isinstance(data, dict):
            raise LearningToolError("学习画像格式无效。")
        return {
            "solved_count": int(data.get("solvedCount") or 0),
            "submission_count": int(data.get("submissionCount") or 0),
            "streak_days": int(data.get("streakDays") or 0),
        }

    def _submissions(self, question_id: str) -> dict[str, Any]:
        rows = self._get("/friend/user/question/submission/list", {"questionId": question_id})
        if not isinstance(rows, list):
            raise LearningToolError("提交记录格式无效。")
        recent = []
        for row in rows[:10]:
            if not isinstance(row, dict):
                continue
            recent.append({
                "status": "ACCEPTED" if row.get("pass") == 1 else "FAILED" if row.get("pass") == 0 else "PENDING",
                "message": str(row.get("exeMessage") or "")[:160],
                "submitted_at": str(row.get("createTime") or "")[:40],
            })
        return {"question_id": question_id, "recent": recent}

    def _questions(self) -> list[dict[str, Any]]:
        payload = self._get_envelope("/friend/question/semiLogin/list", {"pageNum": 1, "pageSize": 30})
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise LearningToolError("题目列表格式无效。")
        result = []
        for row in rows[:30]:
            if not isinstance(row, dict):
                continue
            question_id = str(row.get("questionId") or "")
            title = row.get("title")
            if not question_id.isdecimal() or not isinstance(title, str) or not title.strip():
                continue
            result.append({
                "question_id": question_id,
                "title": title.strip()[:120],
                "difficulty": row.get("difficulty"),
                "knowledge_tags": str(row.get("knowledgeTags") or "")[:160],
                "estimated_minutes": row.get("estimatedMinutes"),
            })
        return result

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._get_envelope(path, params).get("data")

    def _get_envelope(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client = self.client or httpx
        response = client.get(
            f"{self.base_url}{path}",
            params=params,
            headers={"Authorization": self.authorization},
            timeout=5.0,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("code") != 1000:
            raise LearningToolError("学习数据服务返回失败。")
        return payload
