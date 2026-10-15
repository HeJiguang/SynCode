from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from typing import Any, Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.learning_memory.models import LearningMemory, LearningMemoryEvidence, LearningStateMemory, MemoryLevel


def _json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except (json.JSONDecodeError, TypeError):
        return fallback


def _utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _terms(value: str) -> set[str]:
    text_value = value.lower()
    result = set(re.findall(r"[a-z0-9_]+", text_value))
    for chunk in re.findall(r"[\u4e00-\u9fff]+", text_value):
        if len(chunk) == 1:
            result.add(chunk)
        else:
            result.update(chunk[index:index + 2] for index in range(len(chunk) - 1))
    return result


class LearningMemoryRepository:
    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)

    def close(self) -> None:
        self.engine.dispose()

    @staticmethod
    def _user_id(value: str) -> None:
        if not value.isdecimal():
            raise ValueError("Learning memory user identity is invalid.")

    def source_users(self) -> list[str]:
        with self.engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT user_id FROM tb_user_submit WHERE judge_status = 1 AND pass IN (0, 1) "
                "UNION SELECT user_id FROM tb_user_exam WHERE score IS NOT NULL ORDER BY user_id"
            )).scalars().all()
        return [str(value) for value in rows]

    def source_fingerprint(self, *, user_id: str) -> str:
        self._user_id(user_id)
        with self.engine.connect() as connection:
            submissions = connection.execute(
                text(
                    "SELECT COUNT(*) AS row_count, MAX(s.submit_id) AS max_id, "
                    "MAX(COALESCE(s.update_time, s.finish_time, s.create_time)) AS max_time, "
                    "SUM(COALESCE(s.pass, 0)) AS pass_sum, SUM(COALESCE(s.score, 0)) AS score_sum, "
                    "SUM(COALESCE(s.use_time, 0)) AS runtime_sum, SUM(COALESCE(s.use_memory, 0)) AS memory_sum, "
                    "SUM(LENGTH(COALESCE(s.exe_message, ''))) AS message_size, "
                    "SUM(LENGTH(COALESCE(s.last_error, ''))) AS error_size, "
                    "SUM(COALESCE(q.difficulty, 0)) AS difficulty_sum, "
                    "SUM(LENGTH(COALESCE(q.title, '')) + LENGTH(COALESCE(q.algorithm_tag, '')) "
                    "+ LENGTH(COALESCE(q.knowledge_tags, ''))) AS question_metadata_size, "
                    "MAX(q.update_time) AS question_max_time "
                    "FROM tb_user_submit s JOIN tb_question q ON q.question_id = s.question_id "
                    "WHERE s.user_id = :user_id AND s.judge_status = 1 AND s.pass IN (0, 1)"
                ),
                {"user_id": user_id},
            ).mappings().one()
            exams = connection.execute(
                text(
                    "SELECT COUNT(*) AS row_count, MAX(ue.user_exam_id) AS max_id, "
                    "MAX(COALESCE(ue.update_time, ue.create_time)) AS max_time, "
                    "SUM(COALESCE(ue.score, 0)) AS score_sum, "
                    "SUM(COALESCE(ue.exam_rank, 0)) AS rank_sum, "
                    "SUM(LENGTH(COALESCE(e.title, ''))) AS exam_metadata_size, "
                    "MAX(e.update_time) AS exam_max_time "
                    "FROM tb_user_exam ue JOIN tb_exam e ON e.exam_id = ue.exam_id "
                    "WHERE ue.user_id = :user_id AND ue.score IS NOT NULL"
                ),
                {"user_id": user_id},
            ).mappings().one()
        canonical = json.dumps(
            {"submissions": dict(submissions), "exams": dict(exams)},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return sha256(canonical.encode()).hexdigest()

    def projection_state(self, *, user_id: str) -> dict[str, Any] | None:
        self._user_id(user_id)
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT source_fingerprint, event_count, episode_count, pattern_count, "
                    "indexed_fingerprint, last_sync_at, last_indexed_at "
                    "FROM tb_ai_learning_memory_projection_state WHERE user_id = :user_id LIMIT 1"
                ),
                {"user_id": user_id},
            ).mappings().first()
        return dict(row) if row else None

    def save_projection_state(
        self,
        *,
        user_id: str,
        source_fingerprint: str,
        counts: dict[str, int],
        indexed_fingerprint: str | None,
    ) -> None:
        self._user_id(user_id)
        with self.engine.begin() as connection:
            exists = connection.execute(
                text("SELECT user_id FROM tb_ai_learning_memory_projection_state WHERE user_id = :user_id"),
                {"user_id": user_id},
            ).first()
            params = {
                "user_id": user_id,
                "source_fingerprint": source_fingerprint,
                "event_count": counts["events"],
                "episode_count": counts["episodes"],
                "pattern_count": counts["patterns"],
                "indexed_fingerprint": indexed_fingerprint,
            }
            if exists:
                connection.execute(
                    text(
                        """
                        UPDATE tb_ai_learning_memory_projection_state
                        SET source_fingerprint = :source_fingerprint,
                            event_count = :event_count, episode_count = :episode_count,
                            pattern_count = :pattern_count,
                            indexed_fingerprint = :indexed_fingerprint,
                            last_sync_at = CURRENT_TIMESTAMP,
                            last_indexed_at = CASE WHEN :indexed_fingerprint IS NOT NULL
                                THEN CURRENT_TIMESTAMP ELSE last_indexed_at END,
                            update_time = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id
                        """
                    ),
                    params,
                )
            else:
                connection.execute(
                    text(
                        """
                        INSERT INTO tb_ai_learning_memory_projection_state (
                            user_id, source_fingerprint, event_count, episode_count, pattern_count,
                            indexed_fingerprint, last_sync_at, last_indexed_at, create_time, update_time
                        ) VALUES (
                            :user_id, :source_fingerprint, :event_count, :episode_count, :pattern_count,
                            :indexed_fingerprint, CURRENT_TIMESTAMP,
                            CASE WHEN :indexed_fingerprint IS NOT NULL THEN CURRENT_TIMESTAMP ELSE NULL END,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    params,
                )

    def source_submissions(self, *, user_id: str) -> list[dict[str, Any]]:
        self._user_id(user_id)
        statement = text(
            """
            SELECT s.submit_id, s.question_id, s.exam_id, s.program_type, s.pass, s.score,
                   s.exe_message, s.use_time, s.use_memory, s.judge_status, s.last_error,
                   COALESCE(s.finish_time, s.update_time, s.create_time) AS occurred_at,
                   q.title, q.difficulty, q.algorithm_tag, q.knowledge_tags
            FROM tb_user_submit s
            JOIN tb_question q ON q.question_id = s.question_id
            WHERE s.user_id = :user_id AND s.judge_status = 1 AND s.pass IN (0, 1)
            ORDER BY COALESCE(s.finish_time, s.update_time, s.create_time), s.submit_id
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement, {"user_id": user_id}).mappings().all()
        return [dict(row) for row in rows]

    def source_exams(self, *, user_id: str) -> list[dict[str, Any]]:
        self._user_id(user_id)
        statement = text(
            """
            SELECT ue.user_exam_id, ue.exam_id, ue.score, ue.exam_rank,
                   e.title, COALESCE(ue.update_time, ue.create_time, e.end_time) AS occurred_at
            FROM tb_user_exam ue
            JOIN tb_exam e ON e.exam_id = ue.exam_id
            WHERE ue.user_id = :user_id AND ue.score IS NOT NULL
            ORDER BY COALESCE(ue.update_time, ue.create_time, e.end_time), ue.user_exam_id
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement, {"user_id": user_id}).mappings().all()
        return [dict(row) for row in rows]

    def replace_user_projection(self, *, user_id: str, memories: Iterable[LearningMemory]) -> dict[str, int]:
        self._user_id(user_id)
        rows = list(memories)
        if any(memory.user_id != user_id for memory in rows):
            raise ValueError("Learning memory projection contains another user's data.")
        with self.engine.begin() as connection:
            memory_ids = connection.execute(
                text("SELECT memory_id FROM tb_ai_learning_memory WHERE user_id = :user_id"),
                {"user_id": user_id},
            ).scalars().all()
            for offset in range(0, len(memory_ids), 200):
                chunk = memory_ids[offset:offset + 200]
                params = {}
                keys = []
                for index, memory_id in enumerate(chunk):
                    key = f"memory_{index}"
                    params[key] = memory_id
                    keys.append(f":{key}")
                connection.execute(
                    text("DELETE FROM tb_ai_learning_memory_evidence WHERE memory_id IN (" + ",".join(keys) + ")"),
                    params,
                )
            connection.execute(
                text("DELETE FROM tb_ai_learning_memory WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            for memory in rows:
                connection.execute(
                    text(
                        """
                        INSERT INTO tb_ai_learning_memory (
                            memory_id, user_id, memory_level, memory_type, title, summary,
                            knowledge_tags_json, error_type, memory_status, confidence,
                            occurrence_count, source_type, source_id, occurred_at,
                            first_seen_at, last_seen_at, content_hash, structured_payload,
                            create_time, update_time
                        ) VALUES (
                            :memory_id, :user_id, :memory_level, :memory_type, :title, :summary,
                            :knowledge_tags_json, :error_type, :memory_status, :confidence,
                            :occurrence_count, :source_type, :source_id, :occurred_at,
                            :first_seen_at, :last_seen_at, :content_hash, :structured_payload,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {
                        "memory_id": memory.memory_id,
                        "user_id": user_id,
                        "memory_level": memory.level,
                        "memory_type": memory.memory_type,
                        "title": memory.title,
                        "summary": memory.summary,
                        "knowledge_tags_json": json.dumps(memory.knowledge_tags, ensure_ascii=False),
                        "error_type": memory.error_type,
                        "memory_status": memory.status,
                        "confidence": memory.confidence,
                        "occurrence_count": memory.occurrence_count,
                        "source_type": memory.source_type,
                        "source_id": memory.source_id,
                        "occurred_at": _utc_naive(memory.occurred_at),
                        "first_seen_at": _utc_naive(memory.first_seen_at),
                        "last_seen_at": _utc_naive(memory.last_seen_at),
                        "content_hash": memory.content_hash,
                        "structured_payload": json.dumps(memory.payload, ensure_ascii=False, separators=(",", ":"), default=str),
                    },
                )
                for evidence in memory.evidence:
                    self._insert_evidence(connection, memory.memory_id, evidence)
        return {
            "total": len(rows),
            "events": sum(1 for row in rows if row.level == "event"),
            "episodes": sum(1 for row in rows if row.level == "episode"),
            "patterns": sum(1 for row in rows if row.level == "pattern"),
        }

    @staticmethod
    def _insert_evidence(connection, memory_id: str, evidence: LearningMemoryEvidence) -> None:
        connection.execute(
            text(
                """
                INSERT INTO tb_ai_learning_memory_evidence (
                    memory_id, evidence_type, evidence_id, occurred_at,
                    snippet, structured_payload, create_time
                ) VALUES (
                    :memory_id, :evidence_type, :evidence_id, :occurred_at,
                    :snippet, :structured_payload, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "memory_id": memory_id,
                "evidence_type": evidence.evidence_type,
                "evidence_id": evidence.evidence_id,
                "occurred_at": _utc_naive(evidence.occurred_at),
                "snippet": evidence.snippet[:1000],
                "structured_payload": json.dumps(evidence.payload, ensure_ascii=False, separators=(",", ":"), default=str),
            },
        )

    def memories(
        self,
        *,
        user_id: str,
        levels: tuple[MemoryLevel, ...],
        time_range_days: int,
    ) -> list[dict[str, Any]]:
        self._user_id(user_id)
        if not levels:
            return []
        params: dict[str, Any] = {
            "user_id": user_id,
            "cutoff": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=time_range_days),
        }
        level_keys = []
        for index, level in enumerate(levels):
            key = f"level_{index}"
            level_keys.append(f":{key}")
            params[key] = level
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT memory_id, memory_level, memory_type, title, summary,
                           knowledge_tags_json, error_type, memory_status, confidence,
                           occurrence_count, source_type, source_id, occurred_at,
                           first_seen_at, last_seen_at, structured_payload
                    FROM tb_ai_learning_memory
                    WHERE user_id = :user_id
                      AND memory_level IN (""" + ",".join(level_keys) + ") "
                    "AND memory_status != 'superseded' "
                    "AND (last_seen_at IS NULL OR last_seen_at >= :cutoff)"
                ),
                params,
            ).mappings().all()
        return [self._memory_row(row) for row in rows]

    def memories_by_ids(self, *, user_id: str, memory_ids: list[str]) -> list[dict[str, Any]]:
        self._user_id(user_id)
        if not memory_ids:
            return []
        params: dict[str, Any] = {"user_id": user_id}
        keys = []
        for index, memory_id in enumerate(memory_ids):
            key = f"memory_{index}"
            keys.append(f":{key}")
            params[key] = memory_id
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT memory_id, memory_level, memory_type, title, summary, "
                    "knowledge_tags_json, error_type, memory_status, confidence, occurrence_count, "
                    "source_type, source_id, occurred_at, first_seen_at, last_seen_at, structured_payload "
                    "FROM tb_ai_learning_memory WHERE user_id = :user_id AND memory_id IN ("
                    + ",".join(keys) + ")"
                ),
                params,
            ).mappings().all()
        by_id = {str(row["memory_id"]): self._memory_row(row) for row in rows}
        return [by_id[memory_id] for memory_id in memory_ids if memory_id in by_id]

    def search_fallback(
        self,
        *,
        user_id: str,
        query: str,
        levels: tuple[MemoryLevel, ...],
        knowledge_tags: tuple[str, ...],
        time_range_days: int,
        limits: dict[MemoryLevel, int],
    ) -> dict[MemoryLevel, list[dict[str, Any]]]:
        rows = self.memories(user_id=user_id, levels=levels, time_range_days=time_range_days)
        query_terms = _terms(query)
        requested_tags = {tag.lower() for tag in knowledge_tags}
        now = datetime.now(timezone.utc)
        ranked: dict[MemoryLevel, list[tuple[float, dict[str, Any]]]] = {level: [] for level in levels}
        for row in rows:
            tags = {str(tag).lower() for tag in row["knowledge_tags"]}
            if requested_tags and not requested_tags.intersection(tags):
                continue
            searchable = " ".join([
                str(row["title"]), str(row["summary"]), " ".join(tags), str(row.get("error_type") or "")
            ])
            overlap = len(query_terms.intersection(_terms(searchable)))
            when = row.get("last_seen_at") or row.get("occurred_at")
            age_days = 0.0
            if isinstance(when, datetime):
                aware = when.replace(tzinfo=timezone.utc) if when.tzinfo is None else when.astimezone(timezone.utc)
                age_days = max(0.0, (now - aware).total_seconds() / 86400)
            recency = 1 / (1 + age_days / 30)
            status_weight = {"active": 1.0, "improving": 0.75, "resolved": 0.35}.get(str(row["memory_status"]), 0.1)
            score = overlap * 2 + float(row["confidence"]) * status_weight + recency
            if query_terms and overlap == 0 and not requested_tags:
                score *= 0.25
            ranked[row["memory_level"]].append((score, row))
        result: dict[MemoryLevel, list[dict[str, Any]]] = {}
        for level in levels:
            ordered = sorted(
                ranked[level],
                key=lambda item: (-item[0], str(item[1].get("last_seen_at") or ""), item[1]["memory_id"]),
            )
            result[level] = [row for _score, row in ordered[:limits[level]]]
        return result

    def detail(self, *, user_id: str, memory_id: str) -> dict[str, Any]:
        self._user_id(user_id)
        rows = self.memories_by_ids(user_id=user_id, memory_ids=[memory_id])
        if not rows:
            raise ValueError("Learning memory was not found.")
        with self.engine.connect() as connection:
            evidence_rows = connection.execute(
                text(
                    """
                    SELECT evidence_type, evidence_id, occurred_at, snippet, structured_payload
                    FROM tb_ai_learning_memory_evidence
                    WHERE memory_id = :memory_id
                    ORDER BY occurred_at DESC, evidence_type, evidence_id
                    """
                ),
                {"memory_id": memory_id},
            ).mappings().all()
        return {
            **rows[0],
            "evidence": [
                {**dict(row), "payload": _json(row["structured_payload"], {})}
                for row in evidence_rows
            ],
        }

    def learning_state_projection(self, *, user_id: str) -> dict[str, Any] | None:
        self._user_id(user_id)
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT source_fingerprint, state_count, last_sync_at "
                    "FROM tb_ai_learning_state_projection WHERE user_id = :user_id LIMIT 1"
                ),
                {"user_id": user_id},
            ).mappings().first()
        return dict(row) if row else None

    def save_learning_state_projection(
        self,
        *,
        user_id: str,
        source_fingerprint: str,
        state_count: int,
    ) -> None:
        self._user_id(user_id)
        with self.engine.begin() as connection:
            exists = connection.execute(
                text("SELECT user_id FROM tb_ai_learning_state_projection WHERE user_id = :user_id"),
                {"user_id": user_id},
            ).first()
            params = {
                "user_id": user_id,
                "source_fingerprint": source_fingerprint,
                "state_count": state_count,
            }
            if exists:
                connection.execute(
                    text(
                        "UPDATE tb_ai_learning_state_projection "
                        "SET source_fingerprint = :source_fingerprint, state_count = :state_count, "
                        "last_sync_at = CURRENT_TIMESTAMP, update_time = CURRENT_TIMESTAMP "
                        "WHERE user_id = :user_id"
                    ),
                    params,
                )
            else:
                connection.execute(
                    text(
                        "INSERT INTO tb_ai_learning_state_projection "
                        "(user_id, source_fingerprint, state_count, last_sync_at, create_time, update_time) "
                        "VALUES (:user_id, :source_fingerprint, :state_count, CURRENT_TIMESTAMP, "
                        "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    ),
                    params,
                )

    def replace_learning_states(
        self,
        *,
        user_id: str,
        states: Iterable[LearningStateMemory],
    ) -> int:
        self._user_id(user_id)
        rows = list(states)
        if any(state.user_id != user_id for state in rows):
            raise ValueError("Learning state projection contains another user's data.")
        with self.engine.begin() as connection:
            state_ids = connection.execute(
                text("SELECT state_id FROM tb_ai_learning_state_memory WHERE user_id = :user_id"),
                {"user_id": user_id},
            ).scalars().all()
            for offset in range(0, len(state_ids), 200):
                chunk = state_ids[offset:offset + 200]
                params = {f"state_{index}": value for index, value in enumerate(chunk)}
                keys = [f":state_{index}" for index in range(len(chunk))]
                connection.execute(
                    text("DELETE FROM tb_ai_learning_state_evidence WHERE state_id IN (" + ",".join(keys) + ")"),
                    params,
                )
            connection.execute(
                text("DELETE FROM tb_ai_learning_state_memory WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            for state in rows:
                connection.execute(
                    text(
                        """
                        INSERT INTO tb_ai_learning_state_memory (
                            state_id, user_id, knowledge_tag, mastery_level, mastery_score,
                            confidence, trend, priority_score, episode_count, attempt_count,
                            independent_pass_count, error_episode_count, recent_error_types_json,
                            first_practiced_at, last_practiced_at, next_review_at, summary,
                            content_hash, structured_payload, create_time, update_time
                        ) VALUES (
                            :state_id, :user_id, :knowledge_tag, :mastery_level, :mastery_score,
                            :confidence, :trend, :priority_score, :episode_count, :attempt_count,
                            :independent_pass_count, :error_episode_count, :recent_error_types_json,
                            :first_practiced_at, :last_practiced_at, :next_review_at, :summary,
                            :content_hash, :structured_payload, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {
                        "state_id": state.state_id,
                        "user_id": user_id,
                        "knowledge_tag": state.knowledge_tag,
                        "mastery_level": state.mastery_level,
                        "mastery_score": state.mastery_score,
                        "confidence": state.confidence,
                        "trend": state.trend,
                        "priority_score": state.priority_score,
                        "episode_count": state.episode_count,
                        "attempt_count": state.attempt_count,
                        "independent_pass_count": state.independent_pass_count,
                        "error_episode_count": state.error_episode_count,
                        "recent_error_types_json": json.dumps(state.recent_error_types, ensure_ascii=False),
                        "first_practiced_at": _utc_naive(state.first_practiced_at),
                        "last_practiced_at": _utc_naive(state.last_practiced_at),
                        "next_review_at": _utc_naive(state.next_review_at),
                        "summary": state.summary,
                        "content_hash": state.content_hash,
                        "structured_payload": json.dumps(state.payload, ensure_ascii=False, separators=(",", ":")),
                    },
                )
                for item in state.evidence:
                    connection.execute(
                        text(
                            "INSERT INTO tb_ai_learning_state_evidence "
                            "(state_id, memory_id, observed_at, contribution, reason, structured_payload, create_time) "
                            "VALUES (:state_id, :memory_id, :observed_at, :contribution, :reason, "
                            ":structured_payload, CURRENT_TIMESTAMP)"
                        ),
                        {
                            "state_id": state.state_id,
                            "memory_id": item.memory_id,
                            "observed_at": _utc_naive(item.observed_at),
                            "contribution": item.contribution,
                            "reason": item.reason[:500],
                            "structured_payload": json.dumps(item.payload, ensure_ascii=False, separators=(",", ":")),
                        },
                    )
        return len(rows)

    def learning_states(
        self,
        *,
        user_id: str,
        knowledge_tags: tuple[str, ...] = (),
        focus: str = "weakest",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        self._user_id(user_id)
        if focus not in {"weakest", "review_due", "improving", "declining", "all"}:
            raise ValueError("Unsupported learning state focus.")
        params: dict[str, Any] = {"user_id": user_id, "limit": max(1, min(int(limit), 20))}
        clauses = ["user_id = :user_id"]
        if knowledge_tags:
            keys = []
            for index, tag in enumerate(knowledge_tags[:10]):
                key = f"tag_{index}"
                keys.append(f":{key}")
                params[key] = tag
            clauses.append("knowledge_tag IN (" + ",".join(keys) + ")")
        if focus == "review_due":
            clauses.append("next_review_at <= CURRENT_TIMESTAMP")
        elif focus in {"improving", "declining"}:
            clauses.append("trend = :trend")
            params["trend"] = focus
        order = (
            "next_review_at ASC, priority_score DESC"
            if focus == "review_due"
            else "priority_score DESC, last_practiced_at DESC"
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT state_id, knowledge_tag, mastery_level, mastery_score, confidence, trend, "
                    "priority_score, episode_count, attempt_count, independent_pass_count, "
                    "error_episode_count, recent_error_types_json, first_practiced_at, "
                    "last_practiced_at, next_review_at, summary, structured_payload "
                    "FROM tb_ai_learning_state_memory WHERE " + " AND ".join(clauses)
                    + f" ORDER BY {order} LIMIT :limit"
                ),
                params,
            ).mappings().all()
        return [self._learning_state_row(row) for row in rows]

    def learning_state_detail(self, *, user_id: str, state_id: str) -> dict[str, Any]:
        self._user_id(user_id)
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT state_id, knowledge_tag, mastery_level, mastery_score, confidence, trend, "
                    "priority_score, episode_count, attempt_count, independent_pass_count, "
                    "error_episode_count, recent_error_types_json, first_practiced_at, "
                    "last_practiced_at, next_review_at, summary, structured_payload "
                    "FROM tb_ai_learning_state_memory "
                    "WHERE user_id = :user_id AND state_id = :state_id LIMIT 1"
                ),
                {"user_id": user_id, "state_id": state_id},
            ).mappings().first()
            if row is None:
                raise ValueError("Learning state memory was not found.")
            evidence = connection.execute(
                text(
                    "SELECT memory_id, observed_at, contribution, reason, structured_payload "
                    "FROM tb_ai_learning_state_evidence WHERE state_id = :state_id "
                    "ORDER BY observed_at DESC, memory_id"
                ),
                {"state_id": state_id},
            ).mappings().all()
        return {
            **self._learning_state_row(row),
            "evidence": [
                {**dict(item), "payload": _json(item["structured_payload"], {})}
                for item in evidence
            ],
        }

    @staticmethod
    def _memory_row(row) -> dict[str, Any]:
        result = dict(row)
        result["knowledge_tags"] = _json(result.pop("knowledge_tags_json"), [])
        result["payload"] = _json(result.pop("structured_payload"), {})
        result["confidence"] = float(result.get("confidence") or 0.0)
        result["occurrence_count"] = int(result.get("occurrence_count") or 0)
        return result

    @staticmethod
    def _learning_state_row(row) -> dict[str, Any]:
        result = dict(row)
        result["recent_error_types"] = _json(result.pop("recent_error_types_json"), [])
        result["payload"] = _json(result.pop("structured_payload"), {})
        for key in ("mastery_score", "confidence", "priority_score"):
            result[key] = float(result.get(key) or 0.0)
        for key in ("episode_count", "attempt_count", "independent_pass_count", "error_episode_count"):
            result[key] = int(result.get(key) or 0)
        return result
