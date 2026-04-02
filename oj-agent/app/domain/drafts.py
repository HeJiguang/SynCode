from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.runs import utc_now_iso


class DraftType(str, Enum):
    TRAINING_PLAN_REPLACEMENT = "training_plan_replacement"
    BATCH_TASK_STATUS_CHANGE = "batch_task_status_change"
    HIGH_PRIORITY_LEARNING_CONCLUSION = "high_priority_learning_conclusion"
    PROFILE_MAJOR_SHIFT = "profile_major_shift"


class DraftStatus(str, Enum):
    PENDING_USER = "PENDING_USER"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    APPLIED = "APPLIED"


class Draft(BaseModel):
    draft_id: str = Field(default_factory=lambda: f"draft_{uuid4().hex}")
    run_id: str
    write_intent_id: str
    user_id: str
    draft_type: DraftType
    title: str
    summary: str
    current_state: dict[str, Any] = Field(default_factory=dict)
    proposed_state: dict[str, Any] = Field(default_factory=dict)
    diff: dict[str, Any] = Field(default_factory=dict)
    status: DraftStatus = DraftStatus.PENDING_USER
    created_at: str = Field(default_factory=utc_now_iso)
    expires_at: str | None = None
    resolved_at: str | None = None

