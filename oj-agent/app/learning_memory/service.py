from __future__ import annotations

from datetime import date, datetime
import os
from typing import Any, cast

import httpx

from app.learning_memory.models import MEMORY_LEVELS, LearningMemory, MemoryLevel
from app.learning_memory.projector import project_learning_memories
from app.learning_memory.repository import LearningMemoryRepository
from app.learning_memory.search import IndexedLearningMemory, LearningMemoryIndex, owner_hash
from app.skill_governance.search import SkillSearchError


class LearningMemoryService:
    def __init__(
        self,
        repository: LearningMemoryRepository,
        *,
        index: LearningMemoryIndex | None = None,
    ) -> None:
        self.repository = repository
        self.index = index or LearningMemoryIndex()
        self.hash_secret = (
            os.getenv("SYNCODE_LEARNING_MEMORY_HASH_SECRET")
            or os.getenv("SYNCODE_HERMES_PROVISION_KEY")
            or "local-development-only"
        )

    def sync_user(self, *, user_id: str) -> dict[str, Any]:
        if not user_id.isdecimal():
            raise ValueError("Learning memory user identity is invalid.")
        fingerprint = self.repository.source_fingerprint(user_id=user_id)
        state = self.repository.projection_state(user_id=user_id)
        if state and state["source_fingerprint"] == fingerprint:
            counts = {
                "events": int(state["event_count"]),
                "episodes": int(state["episode_count"]),
                "patterns": int(state["pattern_count"]),
            }
            indexed = sum(counts.values()) if state.get("indexed_fingerprint") == fingerprint else 0
            index_error = None
            if self.index.enabled and state.get("indexed_fingerprint") != fingerprint:
                try:
                    rows = self.repository.memories(
                        user_id=user_id,
                        levels=MEMORY_LEVELS,
                        time_range_days=36500,
                    )
                    user_hash = owner_hash(self.hash_secret, user_id)
                    indexed = self.index.replace_user(
                        user_hash,
                        [self._indexed_row(row, user_hash) for row in rows],
                    )
                except (SkillSearchError, httpx.HTTPError, ValueError) as exc:
                    index_error = str(exc)
                self.repository.save_projection_state(
                    user_id=user_id,
                    source_fingerprint=fingerprint,
                    counts=counts,
                    indexed_fingerprint=fingerprint if index_error is None else None,
                )
            return {
                **counts,
                "total": sum(counts.values()),
                "source_submissions": None,
                "source_exams": None,
                "indexed": indexed,
                "index_error": index_error,
                "unchanged": True,
            }
        submissions = self.repository.source_submissions(user_id=user_id)
        exams = self.repository.source_exams(user_id=user_id)
        memories = project_learning_memories(
            user_id=user_id,
            submissions=submissions,
            exams=exams,
        )
        result = self.repository.replace_user_projection(user_id=user_id, memories=memories)
        indexed = 0
        index_error = None
        if self.index.enabled:
            try:
                user_hash = owner_hash(self.hash_secret, user_id)
                indexed = self.index.replace_user(
                    user_hash,
                    [self._indexed(memory, user_hash) for memory in memories],
                )
            except (SkillSearchError, httpx.HTTPError, ValueError) as exc:
                index_error = str(exc)
        self.repository.save_projection_state(
            user_id=user_id,
            source_fingerprint=fingerprint,
            counts=result,
            indexed_fingerprint=fingerprint if self.index.enabled and index_error is None else None,
        )
        return {
            **result,
            "source_submissions": len(submissions),
            "source_exams": len(exams),
            "indexed": indexed,
            "index_error": index_error,
            "unchanged": False,
        }

    def sync_all(self) -> dict[str, Any]:
        metrics = {
            "users": 0,
            "events": 0,
            "episodes": 0,
            "patterns": 0,
            "errors": [],
        }
        for user_id in self.repository.source_users():
            try:
                result = self.sync_user(user_id=user_id)
                metrics["users"] += 1
                for key in ("events", "episodes", "patterns"):
                    metrics[key] += int(result[key])
                if result.get("index_error"):
                    metrics["errors"].append({"user_id": user_id, "error": result["index_error"]})
            except Exception as exc:
                metrics["errors"].append({"user_id": user_id, "error": str(exc)[:500]})
        return metrics

    def recall(
        self,
        *,
        user_id: str,
        query: str,
        levels: list[str] | None = None,
        knowledge_tags: list[str] | None = None,
        time_range_days: int = 90,
        pattern_limit: int = 3,
        episode_limit: int = 5,
        event_limit: int = 5,
    ) -> dict[str, Any]:
        cleaned_query = query.strip()
        if not cleaned_query or len(cleaned_query) > 1000:
            raise ValueError("Learning memory query must contain 1 to 1000 characters.")
        resolved_levels = self._levels(levels)
        tags = tuple(dict.fromkeys(tag.strip() for tag in (knowledge_tags or []) if tag.strip()))[:10]
        days = max(1, min(int(time_range_days), 3650))
        limits: dict[MemoryLevel, int] = {
            "pattern": max(0, min(int(pattern_limit), 10)),
            "episode": max(0, min(int(episode_limit), 20)),
            "event": max(0, min(int(event_limit), 20)),
        }
        resolved_levels = tuple(level for level in resolved_levels if limits[level] > 0)
        sync = self.sync_user(user_id=user_id)

        retrieval_mode = "database"
        retrieval_error = None
        grouped: dict[MemoryLevel, list[dict[str, Any]]]
        if self.index.enabled:
            try:
                memory_ids = self.index.search(
                    owner_hash=owner_hash(self.hash_secret, user_id),
                    query=cleaned_query,
                    levels=resolved_levels,
                    knowledge_tags=tags,
                    time_range_days=days,
                    limits=limits,
                )
                grouped = {
                    level: self.repository.memories_by_ids(user_id=user_id, memory_ids=memory_ids.get(level, []))
                    for level in resolved_levels
                }
                retrieval_mode = "elasticsearch_hybrid"
            except (SkillSearchError, httpx.HTTPError, ValueError) as exc:
                retrieval_error = str(exc)
                grouped = self.repository.search_fallback(
                    user_id=user_id,
                    query=cleaned_query,
                    levels=resolved_levels,
                    knowledge_tags=tags,
                    time_range_days=days,
                    limits=limits,
                )
                retrieval_mode = "database_fallback"
        else:
            grouped = self.repository.search_fallback(
                user_id=user_id,
                query=cleaned_query,
                levels=resolved_levels,
                knowledge_tags=tags,
                time_range_days=days,
                limits=limits,
            )
        return {
            "memory_domain": "problem_solving",
            "query": cleaned_query,
            "retrieval_mode": retrieval_mode,
            "retrieval_error": retrieval_error,
            "patterns": [self._public(row) for row in grouped.get("pattern", [])],
            "episodes": [self._public(row) for row in grouped.get("episode", [])],
            "events": [self._public(row) for row in grouped.get("event", [])],
            "projection": {
                "events": sync["events"],
                "episodes": sync["episodes"],
                "patterns": sync["patterns"],
            },
        }

    def detail(self, *, user_id: str, memory_id: str) -> dict[str, Any]:
        if len(memory_id) != 64 or any(character not in "0123456789abcdef" for character in memory_id):
            raise ValueError("Learning memory id is invalid.")
        return self._public(self.repository.detail(user_id=user_id, memory_id=memory_id), include_evidence=True)

    @staticmethod
    def _levels(levels: list[str] | None) -> tuple[MemoryLevel, ...]:
        if not levels:
            return MEMORY_LEVELS
        resolved = tuple(dict.fromkeys(level.strip().lower() for level in levels))
        invalid = [level for level in resolved if level not in MEMORY_LEVELS]
        if invalid:
            raise ValueError(f"Unsupported learning memory levels: {', '.join(invalid)}")
        return cast(tuple[MemoryLevel, ...], resolved)

    @staticmethod
    def _indexed(memory: LearningMemory, user_hash: str) -> IndexedLearningMemory:
        return IndexedLearningMemory(
            memory_id=memory.memory_id,
            owner_hash=user_hash,
            level=memory.level,
            memory_type=memory.memory_type,
            title=memory.title,
            summary=memory.summary,
            knowledge_tags=memory.knowledge_tags,
            error_type=memory.error_type,
            status=memory.status,
            confidence=memory.confidence,
            occurrence_count=memory.occurrence_count,
            occurred_at=memory.occurred_at,
            last_seen_at=memory.last_seen_at,
        )

    @classmethod
    def _indexed_row(cls, row: dict[str, Any], user_hash: str) -> IndexedLearningMemory:
        return IndexedLearningMemory(
            memory_id=str(row["memory_id"]),
            owner_hash=user_hash,
            level=cast(MemoryLevel, row["memory_level"]),
            memory_type=str(row["memory_type"]),
            title=str(row["title"]),
            summary=str(row["summary"]),
            knowledge_tags=tuple(str(tag) for tag in row.get("knowledge_tags") or []),
            error_type=str(row["error_type"]) if row.get("error_type") else None,
            status=str(row["memory_status"]),
            confidence=float(row.get("confidence") or 0.0),
            occurrence_count=int(row.get("occurrence_count") or 0),
            occurred_at=cls._datetime(row.get("occurred_at")),
            last_seen_at=cls._datetime(row.get("last_seen_at")),
        )

    @classmethod
    def _public(cls, row: dict[str, Any], *, include_evidence: bool = False) -> dict[str, Any]:
        keys = (
            "memory_id", "memory_level", "memory_type", "title", "summary",
            "knowledge_tags", "error_type", "memory_status", "confidence",
            "occurrence_count", "occurred_at", "first_seen_at", "last_seen_at",
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

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
