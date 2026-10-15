from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Any

from app.learning_memory.repository import LearningMemoryRepository
from app.learning_memory.service import LearningMemoryService
from app.learning_memory.state_projector import LEARNING_STATE_MODEL_VERSION, project_learning_states


class LearningStateService:
    def __init__(
        self,
        repository: LearningMemoryRepository,
        memory_service: LearningMemoryService,
    ) -> None:
        self.repository = repository
        self.memory_service = memory_service

    def sync_user(self, *, user_id: str) -> dict[str, Any]:
        if not user_id.isdecimal():
            raise ValueError("Learning state user identity is invalid.")
        memory_sync = self.memory_service.sync_user(user_id=user_id)
        source_fingerprint = self.repository.source_fingerprint(user_id=user_id)
        fingerprint = sha256(
            f"{source_fingerprint}\0{LEARNING_STATE_MODEL_VERSION}\0"
            f"{datetime.now(timezone.utc).date().isoformat()}".encode()
        ).hexdigest()
        projection = self.repository.learning_state_projection(user_id=user_id)
        if projection and projection["source_fingerprint"] == fingerprint:
            return {
                "states": int(projection["state_count"]),
                "unchanged": True,
                "problem_memory": memory_sync,
            }

        episodes = self.repository.memories(
            user_id=user_id,
            levels=("episode",),
            time_range_days=36500,
        )
        states = project_learning_states(user_id=user_id, episodes=episodes)
        state_count = self.repository.replace_learning_states(user_id=user_id, states=states)
        self.repository.save_learning_state_projection(
            user_id=user_id,
            source_fingerprint=fingerprint,
            state_count=state_count,
        )
        return {
            "states": state_count,
            "unchanged": False,
            "problem_memory": memory_sync,
        }

    def sync_all(self) -> dict[str, Any]:
        result: dict[str, Any] = {"users": 0, "states": 0, "errors": []}
        for user_id in self.repository.source_users():
            try:
                synced = self.sync_user(user_id=user_id)
                result["users"] += 1
                result["states"] += int(synced["states"])
                problem_error = synced["problem_memory"].get("index_error")
                if problem_error:
                    result["errors"].append({"user_id": user_id, "error": problem_error})
            except Exception as exc:
                result["errors"].append({"user_id": user_id, "error": str(exc)[:500]})
        return result

    def recall(
        self,
        *,
        user_id: str,
        knowledge_tags: list[str] | None = None,
        focus: str = "weakest",
        limit: int = 10,
    ) -> dict[str, Any]:
        tags = tuple(
            dict.fromkeys(tag.strip().casefold()[:100] for tag in (knowledge_tags or []) if tag.strip())
        )[:10]
        sync = self.sync_user(user_id=user_id)
        rows = self.repository.learning_states(
            user_id=user_id,
            knowledge_tags=tags,
            focus=focus.strip().lower(),
            limit=limit,
        )
        return {
            "memory_domain": "learning_state",
            "focus": focus.strip().lower(),
            "states": [self._public(row) for row in rows],
            "projection": {"states": sync["states"], "unchanged": sync["unchanged"]},
        }

    def detail(self, *, user_id: str, state_id: str) -> dict[str, Any]:
        if len(state_id) != 64 or any(character not in "0123456789abcdef" for character in state_id):
            raise ValueError("Learning state id is invalid.")
        self.sync_user(user_id=user_id)
        return self._public(
            self.repository.learning_state_detail(user_id=user_id, state_id=state_id),
            include_evidence=True,
        )

    @classmethod
    def _public(cls, row: dict[str, Any], *, include_evidence: bool = False) -> dict[str, Any]:
        keys = (
            "state_id", "knowledge_tag", "mastery_level", "mastery_score", "confidence",
            "trend", "priority_score", "episode_count", "attempt_count",
            "independent_pass_count", "error_episode_count", "recent_error_types",
            "first_practiced_at", "last_practiced_at", "next_review_at", "summary",
        )
        result = {key: cls._json_value(row.get(key)) for key in keys}
        result["payload"] = row.get("payload") or {}
        if include_evidence:
            result["evidence"] = [
                {key: cls._json_value(value) for key, value in evidence.items()}
                for evidence in row.get("evidence") or []
            ]
        return result

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value
