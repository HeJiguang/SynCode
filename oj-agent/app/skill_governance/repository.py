from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from typing import Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

from app.skill_governance.storage import SkillDocument, package_json


_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _next_version(current: str | None) -> str:
    if not current:
        return "1.0.0"
    match = _SEMVER_RE.fullmatch(current)
    if not match:
        return f"1.0.{int(sha256(current.encode()).hexdigest()[:4], 16) + 1}"
    major, minor, patch = (int(value) for value in match.groups())
    return f"{major}.{minor}.{patch + 1}"


def _json_value(value):
    if value is None or isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None


class SkillGovernanceRepository:
    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)

    def close(self) -> None:
        self.engine.dispose()

    def sync_personal_skills(
        self,
        *,
        user_id: str,
        profile: str,
        documents: Iterable[SkillDocument],
        archive_missing: bool = True,
    ) -> dict[str, int]:
        if not user_id.isdecimal() or profile != f"syncode-u{user_id}":
            raise ValueError("Personal Skill identity is invalid.")
        created = 0
        versioned = 0
        unchanged = 0
        active_ids: list[str] = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with self.engine.begin() as connection:
            for document in documents:
                row = connection.execute(
                    text(
                        """
                        SELECT skill_id, current_version
                        FROM tb_ai_skill
                        WHERE scope = 'personal' AND owner_user_id = :user_id AND skill_name = :skill_name
                        LIMIT 1
                        """
                    ),
                    {"user_id": user_id, "skill_name": document.name},
                ).mappings().first()
                if row:
                    skill_id = str(row["skill_id"])
                    current_version = str(row["current_version"])
                else:
                    suffix = sha256(f"{user_id}\0{document.name}".encode()).hexdigest()[:16]
                    skill_id = f"personal:{user_id}:{suffix}"
                    current_version = ""
                    connection.execute(
                        text(
                            """
                            INSERT INTO tb_ai_skill (
                                skill_id, skill_name, display_name, description, scope, owner_user_id,
                                category, lifecycle_status, current_version, source_path,
                                last_seen_at, create_time, update_time
                            ) VALUES (
                                :skill_id, :skill_name, :display_name, :description, 'personal', :user_id,
                                :category, 'active', '0.0.0', :source_path,
                                :last_seen_at, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                            )
                            """
                        ),
                        {
                            "skill_id": skill_id,
                            "skill_name": document.name,
                            "display_name": document.display_name,
                            "description": document.description,
                            "user_id": user_id,
                            "category": document.category,
                            "source_path": document.relative_path,
                            "last_seen_at": now,
                        },
                    )
                    created += 1
                active_ids.append(skill_id)
                current = connection.execute(
                    text(
                        """
                        SELECT content_hash
                        FROM tb_ai_skill_version
                        WHERE skill_id = :skill_id AND version = :version
                        LIMIT 1
                        """
                    ),
                    {"skill_id": skill_id, "version": current_version},
                ).mappings().first()
                if current and current["content_hash"] == document.content_hash:
                    unchanged += 1
                    next_version = current_version
                else:
                    next_version = _next_version(current_version if current_version != "0.0.0" else None)
                    connection.execute(
                        text(
                            """
                            INSERT INTO tb_ai_skill_version (
                                skill_id, version, content_hash, source_type, review_status,
                                content_uri, content_text, package_json, metadata_json,
                                created_by_type, created_by, create_time
                            ) VALUES (
                                :skill_id, :version, :content_hash, 'personal', 'approved',
                                :content_uri, :content_text, :package_json, :metadata_json,
                                'hermes', :created_by, CURRENT_TIMESTAMP
                            )
                            """
                        ),
                        {
                            "skill_id": skill_id,
                            "version": next_version,
                            "content_hash": document.content_hash,
                            "content_uri": f"profile://{profile}/skills/{document.relative_path}",
                            "content_text": document.content,
                            "package_json": package_json(document.package),
                            "metadata_json": json.dumps(
                                {"modified_at": document.modified_at.isoformat()},
                                separators=(",", ":"),
                            ),
                            "created_by": profile,
                        },
                    )
                    versioned += 1
                connection.execute(
                    text(
                        """
                        UPDATE tb_ai_skill
                        SET display_name = :display_name, description = :description, category = :category,
                            lifecycle_status = 'active', current_version = :current_version,
                            source_path = :source_path, last_seen_at = :last_seen_at,
                            archived_at = NULL, update_time = CURRENT_TIMESTAMP
                        WHERE skill_id = :skill_id
                        """
                    ),
                    {
                        "skill_id": skill_id,
                        "display_name": document.display_name,
                        "description": document.description,
                        "category": document.category,
                        "current_version": next_version,
                        "source_path": document.relative_path,
                        "last_seen_at": now,
                    },
                )
            archived = (
                self._mark_missing_personal_archived(connection, user_id=user_id, active_ids=active_ids)
                if archive_missing
                else 0
            )
        return {"created": created, "versioned": versioned, "unchanged": unchanged, "archived": archived}

    @staticmethod
    def _mark_missing_personal_archived(
        connection: Connection,
        *,
        user_id: str,
        active_ids: list[str],
    ) -> int:
        params: dict[str, object] = {"user_id": user_id}
        exclusion = ""
        if active_ids:
            placeholders = []
            for index, skill_id in enumerate(active_ids):
                key = f"active_{index}"
                placeholders.append(f":{key}")
                params[key] = skill_id
            exclusion = f" AND skill_id NOT IN ({','.join(placeholders)})"
        result = connection.execute(
            text(
                """
                UPDATE tb_ai_skill
                SET lifecycle_status = 'archived', archived_at = CURRENT_TIMESTAMP,
                    update_time = CURRENT_TIMESTAMP
                WHERE scope = 'personal' AND owner_user_id = :user_id
                  AND lifecycle_status = 'active'
                """ + exclusion
            ),
            params,
        )
        return int(result.rowcount or 0)

    def list_personal_skills(self, *, user_id: str, include_archived: bool = True) -> list[dict]:
        if not user_id.isdecimal():
            raise ValueError("Personal Skill identity is invalid.")
        status_sql = "" if include_archived else "AND s.lifecycle_status = 'active'"
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    f"""
                    SELECT s.skill_id, s.skill_name, s.display_name, s.description, s.category,
                           s.lifecycle_status, s.current_version, s.create_time, s.update_time,
                           COUNT(e.event_id) AS usage_count_30d, MAX(e.occurred_at) AS last_used_at
                    FROM tb_ai_skill s
                    LEFT JOIN tb_ai_skill_usage_event e
                      ON e.user_id = s.owner_user_id AND e.skill_name = s.skill_name
                     AND e.event_type = 'skill.invoked' AND e.occurred_at >= :cutoff
                    WHERE s.scope = 'personal' AND s.owner_user_id = :user_id {status_sql}
                    GROUP BY s.skill_id, s.skill_name, s.display_name, s.description, s.category,
                             s.lifecycle_status, s.current_version, s.create_time, s.update_time
                    ORDER BY s.lifecycle_status, s.update_time DESC, s.skill_name
                    """
                ),
                {"user_id": user_id, "cutoff": cutoff},
            ).mappings().all()
        return [dict(row) for row in rows]

    def list_personal_versions(self, *, user_id: str, skill_name: str) -> list[dict]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT v.version, v.content_hash, v.metadata_json, v.create_time
                    FROM tb_ai_skill s
                    JOIN tb_ai_skill_version v ON v.skill_id = s.skill_id
                    WHERE s.scope = 'personal' AND s.owner_user_id = :user_id
                      AND s.skill_name = :skill_name
                    ORDER BY v.create_time DESC, v.version DESC
                    """
                ),
                {"user_id": user_id, "skill_name": skill_name},
            ).mappings().all()
        return [
            {**dict(row), "metadata": _json_value(row["metadata_json"])}
            for row in rows
        ]

    def personal_version_package(self, *, user_id: str, skill_name: str, version: str) -> dict[str, str]:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT v.package_json
                    FROM tb_ai_skill s
                    JOIN tb_ai_skill_version v ON v.skill_id = s.skill_id
                    WHERE s.scope = 'personal' AND s.owner_user_id = :user_id
                      AND s.skill_name = :skill_name AND v.version = :version
                    LIMIT 1
                    """
                ),
                {"user_id": user_id, "skill_name": skill_name, "version": version},
            ).mappings().first()
        package = _json_value(row["package_json"]) if row else None
        if not isinstance(package, dict) or "SKILL.md" not in package:
            raise ValueError("Personal Skill version was not found.")
        return {str(path): str(content) for path, content in package.items()}

    def active_personal_skills(self) -> list[dict]:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT s.skill_id, s.skill_name, s.display_name, s.description, s.owner_user_id,
                           s.category, s.current_version, v.content_hash, v.content_text,
                           COUNT(e.event_id) AS usage_count_30d, MAX(e.occurred_at) AS last_used_at
                    FROM tb_ai_skill s
                    JOIN tb_ai_skill_version v
                      ON v.skill_id = s.skill_id AND v.version = s.current_version
                    LEFT JOIN tb_ai_skill_usage_event e
                      ON e.user_id = s.owner_user_id AND e.skill_name = s.skill_name
                     AND e.event_type = 'skill.invoked' AND e.occurred_at >= :cutoff
                    WHERE s.scope = 'personal' AND s.lifecycle_status = 'active'
                    GROUP BY s.skill_id, s.skill_name, s.display_name, s.description, s.owner_user_id,
                             s.category, s.current_version, v.content_hash, v.content_text
                    ORDER BY s.skill_id
                    """
                ),
                {"cutoff": cutoff},
            ).mappings().all()
        return [dict(row) for row in rows]

    def upsert_promotion_candidate(
        self,
        *,
        cluster_key: str,
        title: str,
        proposed_skill_name: str,
        category: str | None,
        summary: str,
        draft_content: str | None,
        members: list[dict],
        similarity_method: str,
    ) -> tuple[str, bool]:
        candidate_id = sha256(f"promotion\0{cluster_key}".encode()).hexdigest()
        distinct_owner_count = len({str(member["owner_user_id"]) for member in members})
        usage_count = sum(int(member.get("usage_count_30d") or 0) for member in members)
        min_similarity = min(float(member.get("similarity_score") or 0.0) for member in members)
        created = False
        candidate_status = "reviewing" if draft_content else "discovered"
        with self.engine.begin() as connection:
            existing = connection.execute(
                text(
                    "SELECT candidate_id, status FROM tb_ai_skill_promotion_candidate "
                    "WHERE cluster_key = :cluster_key LIMIT 1"
                ),
                {"cluster_key": cluster_key},
            ).mappings().first()
            if existing:
                candidate_id = str(existing["candidate_id"])
                if existing["status"] in {"discovered", "reviewing"}:
                    connection.execute(
                        text(
                            """
                            UPDATE tb_ai_skill_promotion_candidate
                            SET title = :title, proposed_skill_name = :proposed_skill_name,
                                category = :category, summary = :summary, draft_content = :draft_content,
                                distinct_owner_count = :distinct_owner_count, member_count = :member_count,
                                usage_count_30d = :usage_count_30d, min_similarity = :min_similarity,
                                similarity_method = :similarity_method, status = :status,
                                update_time = CURRENT_TIMESTAMP
                            WHERE candidate_id = :candidate_id
                            """
                        ),
                        {
                            "candidate_id": candidate_id,
                            "title": title,
                            "proposed_skill_name": proposed_skill_name,
                            "category": category,
                            "summary": summary,
                            "draft_content": draft_content,
                            "distinct_owner_count": distinct_owner_count,
                            "member_count": len(members),
                            "usage_count_30d": usage_count,
                            "min_similarity": min_similarity,
                            "similarity_method": similarity_method,
                            "status": candidate_status,
                        },
                    )
            else:
                connection.execute(
                    text(
                        """
                        INSERT INTO tb_ai_skill_promotion_candidate (
                            candidate_id, cluster_key, title, proposed_skill_name, category,
                            status, summary, draft_content, distinct_owner_count, member_count,
                            usage_count_30d, min_similarity, similarity_method, create_time, update_time
                        ) VALUES (
                            :candidate_id, :cluster_key, :title, :proposed_skill_name, :category,
                            :status, :summary, :draft_content, :distinct_owner_count, :member_count,
                            :usage_count_30d, :min_similarity, :similarity_method,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {
                        "candidate_id": candidate_id,
                        "cluster_key": cluster_key,
                        "title": title,
                        "proposed_skill_name": proposed_skill_name,
                        "category": category,
                        "summary": summary,
                        "draft_content": draft_content,
                        "distinct_owner_count": distinct_owner_count,
                        "member_count": len(members),
                        "usage_count_30d": usage_count,
                        "min_similarity": min_similarity,
                        "similarity_method": similarity_method,
                        "status": candidate_status,
                    },
                )
                created = True
            connection.execute(
                text("DELETE FROM tb_ai_skill_promotion_member WHERE candidate_id = :candidate_id"),
                {"candidate_id": candidate_id},
            )
            for member in members:
                connection.execute(
                    text(
                        """
                        INSERT INTO tb_ai_skill_promotion_member (
                            candidate_id, skill_id, skill_version, owner_hash,
                            similarity_score, redacted_summary, usage_count_30d, create_time
                        ) VALUES (
                            :candidate_id, :skill_id, :skill_version, :owner_hash,
                            :similarity_score, :redacted_summary, :usage_count_30d, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {
                        "candidate_id": candidate_id,
                        "skill_id": member["skill_id"],
                        "skill_version": member["current_version"],
                        "owner_hash": member["owner_hash"],
                        "similarity_score": member.get("similarity_score", 1.0),
                        "redacted_summary": member.get("redacted_summary", ""),
                        "usage_count_30d": member.get("usage_count_30d", 0),
                    },
                )
        return candidate_id, created

    def list_promotion_candidates(self, *, status: str = "reviewing", limit: int = 50) -> list[dict]:
        allowed = {"discovered", "reviewing", "approved", "rejected", "published"}
        if status not in allowed or limit < 1 or limit > 200:
            raise ValueError("Promotion candidate query is invalid.")
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT candidate_id, title, proposed_skill_name, category, status, summary,
                           distinct_owner_count, member_count, usage_count_30d, min_similarity,
                           similarity_method, reviewed_by, review_note, reviewed_at,
                           published_skill_id, published_version, create_time, update_time
                    FROM tb_ai_skill_promotion_candidate
                    WHERE status = :status
                    ORDER BY distinct_owner_count DESC, usage_count_30d DESC, create_time
                    LIMIT :limit
                    """
                ),
                {"status": status, "limit": limit},
            ).mappings().all()
        return [dict(row) for row in rows]

    def promotion_candidate(self, candidate_id: str) -> dict:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT * FROM tb_ai_skill_promotion_candidate "
                    "WHERE candidate_id = :candidate_id LIMIT 1"
                ),
                {"candidate_id": candidate_id},
            ).mappings().first()
            if not row:
                raise ValueError("Promotion candidate was not found.")
            members = connection.execute(
                text(
                    """
                    SELECT skill_id, skill_version, owner_hash, similarity_score,
                           redacted_summary, usage_count_30d
                    FROM tb_ai_skill_promotion_member
                    WHERE candidate_id = :candidate_id
                    ORDER BY similarity_score DESC, skill_id
                    """
                ),
                {"candidate_id": candidate_id},
            ).mappings().all()
        public_members = []
        for member in members:
            owner_ref = sha256(
                f"{candidate_id}\0{member['owner_hash']}".encode()
            ).hexdigest()[:16]
            source_ref = sha256(
                f"{candidate_id}\0{member['owner_hash']}\0{member['skill_id']}".encode()
            ).hexdigest()[:16]
            public_members.append({
                "source_ref": source_ref,
                "owner_ref": owner_ref,
                "skill_version": member["skill_version"],
                "similarity_score": member["similarity_score"],
                "redacted_summary": member["redacted_summary"],
                "usage_count_30d": member["usage_count_30d"],
            })
        return {**dict(row), "members": public_members}

    def reject_promotion(self, *, candidate_id: str, reviewer: str, note: str | None) -> dict:
        return self._finish_promotion_review(
            candidate_id=candidate_id,
            reviewer=reviewer,
            decision="reject",
            note=note,
        )

    def publish_promotion(
        self,
        *,
        candidate_id: str,
        reviewer: str,
        note: str | None,
        name: str,
        category: str | None,
        content: str,
        content_hash: str,
        content_uri: str,
    ) -> dict:
        skill_id = f"platform:{name}"
        with self.engine.begin() as connection:
            candidate = connection.execute(
                text(
                    "SELECT status FROM tb_ai_skill_promotion_candidate "
                    "WHERE candidate_id = :candidate_id LIMIT 1"
                ),
                {"candidate_id": candidate_id},
            ).mappings().first()
            if not candidate or candidate["status"] not in {"discovered", "reviewing"}:
                raise ValueError("Only an open promotion candidate can be published.")
            before_status = str(candidate["status"])
            skill = connection.execute(
                text("SELECT current_version FROM tb_ai_skill WHERE skill_id = :skill_id LIMIT 1"),
                {"skill_id": skill_id},
            ).mappings().first()
            version = _next_version(str(skill["current_version"]) if skill else None)
            if skill:
                connection.execute(
                    text(
                        """
                        UPDATE tb_ai_skill
                        SET category = :category, lifecycle_status = 'active', current_version = :version,
                            description = :description, archived_at = NULL, update_time = CURRENT_TIMESTAMP
                        WHERE skill_id = :skill_id
                        """
                    ),
                    {
                        "skill_id": skill_id,
                        "category": category,
                        "version": version,
                        "description": self._description_from_content(content),
                    },
                )
            else:
                connection.execute(
                    text(
                        """
                        INSERT INTO tb_ai_skill (
                            skill_id, skill_name, display_name, description, scope, owner_user_id,
                            category, lifecycle_status, current_version, source_path,
                            last_seen_at, create_time, update_time
                        ) VALUES (
                            :skill_id, :name, :display_name, :description, 'platform', 0,
                            :category, 'active', :version, :source_path,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {
                        "skill_id": skill_id,
                        "name": name,
                        "display_name": name,
                        "description": self._description_from_content(content),
                        "category": category,
                        "version": version,
                        "source_path": content_uri,
                    },
                )
            connection.execute(
                text(
                    """
                    INSERT INTO tb_ai_skill_version (
                        skill_id, version, content_hash, source_type, review_status,
                        content_uri, content_text, package_json, metadata_json,
                        created_by_type, created_by, source_candidate_id, create_time
                    ) VALUES (
                        :skill_id, :version, :content_hash, 'promotion', 'approved',
                        :content_uri, :content_text, :package_json, :metadata_json,
                        'admin', :reviewer, :candidate_id, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "skill_id": skill_id,
                    "version": version,
                    "content_hash": content_hash,
                    "content_uri": content_uri,
                    "content_text": content,
                    "package_json": json.dumps({"SKILL.md": content}, ensure_ascii=False),
                    "metadata_json": json.dumps({"promotion_candidate_id": candidate_id}),
                    "reviewer": reviewer,
                    "candidate_id": candidate_id,
                },
            )
            release_id = sha256(f"release\0{skill_id}\0{version}".encode()).hexdigest()
            connection.execute(
                text(
                    """
                    INSERT INTO tb_ai_skill_release (
                        release_id, skill_id, version, source_candidate_id, status,
                        published_by, published_at, create_time
                    ) VALUES (
                        :release_id, :skill_id, :version, :candidate_id, 'active',
                        :reviewer, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "release_id": release_id,
                    "skill_id": skill_id,
                    "version": version,
                    "candidate_id": candidate_id,
                    "reviewer": reviewer,
                },
            )
            connection.execute(
                text(
                    """
                    UPDATE tb_ai_skill_promotion_candidate
                    SET status = 'published', proposed_skill_name = :name, category = :category,
                        draft_content = :content, reviewed_by = :reviewer, review_note = :note,
                        reviewed_at = CURRENT_TIMESTAMP, published_skill_id = :skill_id,
                        published_version = :version, update_time = CURRENT_TIMESTAMP
                    WHERE candidate_id = :candidate_id
                    """
                ),
                {
                    "candidate_id": candidate_id,
                    "name": name,
                    "category": category,
                    "content": content,
                    "reviewer": reviewer,
                    "note": note,
                    "skill_id": skill_id,
                    "version": version,
                },
            )
            self._insert_promotion_action(
                connection,
                candidate_id=candidate_id,
                reviewer=reviewer,
                action="publish",
                before_status=before_status,
                after_status="published",
                note=note,
            )
        return {"candidate_id": candidate_id, "skill_id": skill_id, "version": version, "status": "published"}

    def _finish_promotion_review(
        self,
        *,
        candidate_id: str,
        reviewer: str,
        decision: str,
        note: str | None,
    ) -> dict:
        with self.engine.begin() as connection:
            candidate = connection.execute(
                text(
                    "SELECT status FROM tb_ai_skill_promotion_candidate "
                    "WHERE candidate_id = :candidate_id LIMIT 1"
                ),
                {"candidate_id": candidate_id},
            ).mappings().first()
            if not candidate or candidate["status"] not in {"discovered", "reviewing"}:
                raise ValueError("Only an open promotion candidate can be rejected.")
            before_status = str(candidate["status"])
            connection.execute(
                text(
                    """
                    UPDATE tb_ai_skill_promotion_candidate
                    SET status = 'rejected', reviewed_by = :reviewer, review_note = :note,
                        reviewed_at = CURRENT_TIMESTAMP, update_time = CURRENT_TIMESTAMP
                    WHERE candidate_id = :candidate_id
                    """
                ),
                {"candidate_id": candidate_id, "reviewer": reviewer, "note": note},
            )
            self._insert_promotion_action(
                connection,
                candidate_id=candidate_id,
                reviewer=reviewer,
                action=decision,
                before_status=before_status,
                after_status="rejected",
                note=note,
            )
        return {"candidate_id": candidate_id, "status": "rejected"}

    @staticmethod
    def _insert_promotion_action(
        connection: Connection,
        *,
        candidate_id: str,
        reviewer: str,
        action: str,
        before_status: str,
        after_status: str,
        note: str | None,
    ) -> None:
        action_id = sha256(
            f"{candidate_id}\0{reviewer}\0{action}\0{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()
        connection.execute(
            text(
                """
                INSERT INTO tb_ai_skill_promotion_review_action (
                    action_id, candidate_id, reviewer, action, before_status,
                    after_status, note, create_time
                ) VALUES (
                    :action_id, :candidate_id, :reviewer, :action, :before_status,
                    :after_status, :note, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "action_id": action_id,
                "candidate_id": candidate_id,
                "reviewer": reviewer,
                "action": action,
                "before_status": before_status,
                "after_status": after_status,
                "note": note,
            },
        )

    def refresh_lifecycle_reviews(self, *, stale_days: int = 30, max_usage: int = 1) -> int:
        if stale_days < 1 or max_usage < 0:
            raise ValueError("Lifecycle review thresholds are invalid.")
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=stale_days)
        created = 0
        with self.engine.begin() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT s.skill_id, s.skill_name, s.current_version,
                           COUNT(e.event_id) AS usage_count, MAX(e.occurred_at) AS last_used_at
                    FROM tb_ai_skill s
                    LEFT JOIN tb_ai_skill_usage_event e
                      ON e.skill_name = s.skill_name AND e.skill_version = s.current_version
                     AND e.event_type = 'skill.invoked' AND e.occurred_at >= :cutoff
                    WHERE s.scope = 'platform' AND s.lifecycle_status = 'active'
                      AND s.create_time < :cutoff
                    GROUP BY s.skill_id, s.skill_name, s.current_version
                    HAVING COUNT(e.event_id) <= :max_usage
                    """
                ),
                {"cutoff": cutoff, "max_usage": max_usage},
            ).mappings().all()
            for row in rows:
                review_id = sha256(
                    f"lifecycle\0{row['skill_id']}\0{row['current_version']}\0low-use-{stale_days}d-{max_usage}".encode()
                ).hexdigest()
                try:
                    with connection.begin_nested():
                        connection.execute(
                            text(
                                """
                                INSERT INTO tb_ai_skill_lifecycle_review (
                                    review_id, skill_id, skill_version, reason, status,
                                    usage_count_30d, last_used_at, create_time, update_time
                                ) VALUES (
                                    :review_id, :skill_id, :version, :reason, 'pending',
                                    :usage_count, :last_used_at, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                                )
                                """
                            ),
                            {
                                "review_id": review_id,
                                "skill_id": row["skill_id"],
                                "version": row["current_version"],
                                "reason": (
                                    f"At most {max_usage} recorded invocation(s) "
                                    f"in the last {stale_days} days"
                                ),
                                "usage_count": int(row["usage_count"] or 0),
                                "last_used_at": row["last_used_at"],
                            },
                        )
                    created += 1
                except IntegrityError:
                    continue
        return created

    def list_lifecycle_reviews(self, *, status: str = "pending", limit: int = 50) -> list[dict]:
        if status not in {"pending", "kept", "archived"} or not 1 <= limit <= 200:
            raise ValueError("Lifecycle review query is invalid.")
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT r.review_id, r.skill_id, s.skill_name, r.skill_version, r.reason,
                           r.status, r.usage_count_30d, r.last_used_at, r.reviewed_by,
                           r.review_note, r.reviewed_at, r.create_time
                    FROM tb_ai_skill_lifecycle_review r
                    JOIN tb_ai_skill s ON s.skill_id = r.skill_id
                    WHERE r.status = :status
                    ORDER BY r.create_time, r.review_id
                    LIMIT :limit
                    """
                ),
                {"status": status, "limit": limit},
            ).mappings().all()
        return [dict(row) for row in rows]

    def finish_lifecycle_review(
        self,
        *,
        review_id: str,
        reviewer: str,
        decision: str,
        note: str | None,
    ) -> dict:
        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT r.status, r.skill_id, s.skill_name
                    FROM tb_ai_skill_lifecycle_review r
                    JOIN tb_ai_skill s ON s.skill_id = r.skill_id
                    WHERE r.review_id = :review_id LIMIT 1
                    """
                ),
                {"review_id": review_id},
            ).mappings().first()
            if not row or row["status"] != "pending":
                raise ValueError("Lifecycle review is not pending.")
            after = "archived" if decision == "archive" else "kept"
            connection.execute(
                text(
                    """
                    UPDATE tb_ai_skill_lifecycle_review
                    SET status = :status, reviewed_by = :reviewer, review_note = :note,
                        reviewed_at = CURRENT_TIMESTAMP, update_time = CURRENT_TIMESTAMP
                    WHERE review_id = :review_id
                    """
                ),
                {"review_id": review_id, "status": after, "reviewer": reviewer, "note": note},
            )
            if decision == "archive":
                connection.execute(
                    text(
                        """
                        UPDATE tb_ai_skill
                        SET lifecycle_status = 'archived', archived_at = CURRENT_TIMESTAMP,
                            update_time = CURRENT_TIMESTAMP
                        WHERE skill_id = :skill_id
                        """
                    ),
                    {"skill_id": row["skill_id"]},
                )
        return {
            "review_id": review_id,
            "skill_id": row["skill_id"],
            "skill_name": row["skill_name"],
            "status": after,
        }

    def start_heartbeat(self) -> str:
        heartbeat_id = sha256(f"heartbeat\0{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO tb_ai_skill_governance_heartbeat (
                        heartbeat_id, status, started_at, create_time
                    ) VALUES (:heartbeat_id, 'running', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {"heartbeat_id": heartbeat_id},
            )
        return heartbeat_id

    def finish_heartbeat(self, *, heartbeat_id: str, status: str, metrics: dict, error: str | None = None) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE tb_ai_skill_governance_heartbeat
                    SET status = :status, metrics_json = :metrics_json, error_message = :error,
                        finished_at = CURRENT_TIMESTAMP
                    WHERE heartbeat_id = :heartbeat_id
                    """
                ),
                {
                    "heartbeat_id": heartbeat_id,
                    "status": status,
                    "metrics_json": json.dumps(metrics, ensure_ascii=False, separators=(",", ":")),
                    "error": error[:2000] if error else None,
                },
            )

    @staticmethod
    def _description_from_content(content: str) -> str:
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) == 3:
                try:
                    import yaml

                    parsed = yaml.safe_load(parts[1]) or {}
                    if isinstance(parsed, dict):
                        return str(parsed.get("description") or "")[:1000]
                except Exception:
                    pass
        return ""
