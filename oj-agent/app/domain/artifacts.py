from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.runs import utc_now_iso


class ArtifactType(str, Enum):
    ANSWER_CARD = "answer_card"
    DIAGNOSIS_REPORT = "diagnosis_report"
    RECOMMENDATION_PACK = "recommendation_pack"
    TRAINING_PLAN = "training_plan"
    REVIEW_SUMMARY = "review_summary"
    PROFILE_DELTA = "profile_delta"
    WEAKNESS_SNAPSHOT = "weakness_snapshot"
    MESSAGE_PACK = "message_pack"
    RUN_SUMMARY = "run_summary"


class RenderHint(str, Enum):
    MARKDOWN = "markdown"
    DIAGNOSIS = "diagnosis"
    PLAN = "plan"
    PROFILE_DELTA = "profile_delta"
    RECOMMENDATION = "recommendation"
    TIMELINE_CARD = "timeline_card"


class Artifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: f"art_{uuid4().hex}")
    run_id: str
    artifact_type: ArtifactType
    title: str
    summary: str | None = None
    body: dict[str, Any] = Field(default_factory=dict)
    render_hint: RenderHint = RenderHint.MARKDOWN
    version: int = 1
    created_at: str = Field(default_factory=utc_now_iso)

