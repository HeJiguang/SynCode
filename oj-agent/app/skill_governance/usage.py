from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError


RESOURCE_PATTERN = r"^[A-Za-z0-9._:-]{1,192}$"
SKILL_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"


class SkillUsageEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(pattern=RESOURCE_PATTERN)
    event_type: Literal["skill.invoked"]
    occurred_at: datetime
    run_id: str = Field(pattern=RESOURCE_PATTERN)
    session_id: str | None = Field(default=None, pattern=RESOURCE_PATTERN)
    skill_name: str = Field(pattern=SKILL_PATTERN)
    skill_version: str | None = Field(default=None, max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)


class SkillUsageBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(pattern=r"^[0-9]+$")
    profile: str = Field(pattern=r"^syncode-u[0-9]+$")
    events: list[SkillUsageEvent] = Field(min_length=1, max_length=100)


class SkillUsageRepository:
    """Append-only Hermes skill_view invocations used by catalog governance."""

    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)

    def close(self) -> None:
        self.engine.dispose()

    def record_events(
        self,
        *,
        user_id: str,
        profile: str,
        events: Iterable[SkillUsageEvent],
    ) -> tuple[int, int]:
        if not user_id.isdecimal() or profile != f"syncode-u{user_id}":
            raise ValueError("Skill usage identity is invalid.")

        inserted = 0
        duplicates = 0
        version_sql = text(
            "SELECT current_version FROM tb_ai_skill "
            "WHERE skill_name = :skill_name AND lifecycle_status = 'active' "
            "AND ((scope = 'personal' AND owner_user_id = :user_id) OR scope = 'platform') "
            "ORDER BY CASE WHEN scope = 'personal' THEN 0 ELSE 1 END LIMIT 1"
        )
        insert_sql = text(
            """
            INSERT INTO tb_ai_skill_usage_event (
                event_id, user_id, profile_name, run_id, session_id,
                skill_name, skill_version, event_type, occurred_at,
                payload_json, create_time
            ) VALUES (
                :event_id, :user_id, :profile_name, :run_id, :session_id,
                :skill_name, :skill_version, 'skill.invoked', :occurred_at,
                :payload_json, CURRENT_TIMESTAMP
            )
            """
        )
        with self.engine.begin() as connection:
            for event in events:
                skill_version = event.skill_version
                if not skill_version:
                    row = connection.execute(
                        version_sql,
                        {"skill_name": event.skill_name, "user_id": user_id},
                    ).mappings().first()
                    if row:
                        skill_version = str(row["current_version"])
                occurred_at = event.occurred_at
                if occurred_at.tzinfo is not None:
                    occurred_at = occurred_at.astimezone(timezone.utc).replace(tzinfo=None)
                try:
                    with connection.begin_nested():
                        connection.execute(
                            insert_sql,
                            {
                                "event_id": event.event_id,
                                "user_id": user_id,
                                "profile_name": profile,
                                "run_id": event.run_id,
                                "session_id": event.session_id,
                                "skill_name": event.skill_name,
                                "skill_version": skill_version,
                                "occurred_at": occurred_at,
                                "payload_json": json.dumps(
                                    event.payload,
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                    default=str,
                                ),
                            },
                        )
                    inserted += 1
                except IntegrityError:
                    duplicates += 1
        return inserted, duplicates
