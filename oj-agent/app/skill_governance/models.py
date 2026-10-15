from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SKILL_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"
PROFILE_PATTERN = r"^syncode-u[0-9]+$"


class UserSkillRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(pattern=r"^[0-9]+$")
    profile: str = Field(pattern=PROFILE_PATTERN)


class UserSkillMutationRequest(UserSkillRequest):
    skill_name: str = Field(pattern=SKILL_PATTERN)


class UserSkillRollbackRequest(UserSkillMutationRequest):
    version: str = Field(min_length=1, max_length=32)


class GovernanceHeartbeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_distinct_owners: int = Field(default=3, ge=2, le=100)
    neighbor_limit: int = Field(default=20, ge=2, le=100)


class PromotionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer: str = Field(min_length=1, max_length=96)
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=1000)
    proposed_skill_name: str | None = Field(default=None, pattern=SKILL_PATTERN)
    category: str | None = Field(default=None, pattern=SKILL_PATTERN)
    content: str | None = Field(default=None, min_length=1, max_length=1_048_576)


class LifecycleReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer: str = Field(min_length=1, max_length=96)
    decision: Literal["keep", "archive"]
    note: str | None = Field(default=None, max_length=1000)
