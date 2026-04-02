from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.runs import utc_now_iso


class WriteIntentType(str, Enum):
    PROFILE_UPDATE = "profile_update"
    WEAKNESS_TAG_UPDATE = "weakness_tag_update"
    TRAINING_PLAN_RECOMPUTE = "training_plan_recompute"
    TRAINING_PLAN_REPLACE = "training_plan_replace"
    MESSAGE_DELIVERY = "message_delivery"
    REVIEW_SNAPSHOT_WRITE = "review_snapshot_write"


class TargetService(str, Enum):
    OJ_FRIEND = "oj-friend"
    OJ_SYSTEM = "oj-system"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class UserImpactLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class WriteExecutionStatus(str, Enum):
    CREATED = "CREATED"
    PENDING_POLICY = "PENDING_POLICY"
    AUTO_APPROVED = "AUTO_APPROVED"
    DRAFT_REQUIRED = "DRAFT_REQUIRED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class WriteIntent(BaseModel):
    write_intent_id: str = Field(default_factory=lambda: f"wi_{uuid4().hex}")
    run_id: str
    user_id: str
    intent_type: WriteIntentType
    target_service: TargetService
    target_aggregate: str
    payload: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    user_impact_level: UserImpactLevel = UserImpactLevel.LOW
    execution_status: WriteExecutionStatus = WriteExecutionStatus.CREATED
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

