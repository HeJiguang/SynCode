from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.runs import utc_now_iso
from app.domain.write_intents import UserImpactLevel, WriteIntent, WriteIntentType


class PolicyDecisionType(str, Enum):
    AUTO_APPLY = "AUTO_APPLY"
    CREATE_DRAFT = "CREATE_DRAFT"
    BLOCK = "BLOCK"
    DOWNGRADE = "DOWNGRADE"


class PolicyDecision(BaseModel):
    policy_decision_id: str = Field(default_factory=lambda: f"policy_{uuid4().hex}")
    run_id: str
    write_intent_id: str
    decision: PolicyDecisionType
    reasons: list[str] = Field(default_factory=list)
    matched_policies: list[str] = Field(default_factory=list)
    overrideable: bool = True
    requires_user_confirmation: bool = False
    created_at: str = Field(default_factory=utc_now_iso)


AUTO_APPLY_TYPES = {
    WriteIntentType.MESSAGE_DELIVERY,
    WriteIntentType.PROFILE_UPDATE,
    WriteIntentType.WEAKNESS_TAG_UPDATE,
    WriteIntentType.TRAINING_PLAN_RECOMPUTE,
}


def evaluate_balanced_policy(write_intent: WriteIntent) -> PolicyDecision:
    """Apply the learning-first balanced write policy described in the spec."""
    if write_intent.intent_type == WriteIntentType.TRAINING_PLAN_REPLACE:
        return PolicyDecision(
            run_id=write_intent.run_id,
            write_intent_id=write_intent.write_intent_id,
            decision=PolicyDecisionType.CREATE_DRAFT,
            reasons=["Replacing the active learning plan requires user confirmation."],
            matched_policies=["balanced.training_plan_replace.requires_draft"],
            requires_user_confirmation=True,
        )

    if write_intent.user_impact_level == UserImpactLevel.HIGH:
        return PolicyDecision(
            run_id=write_intent.run_id,
            write_intent_id=write_intent.write_intent_id,
            decision=PolicyDecisionType.CREATE_DRAFT,
            reasons=["High-impact learning changes require explicit review."],
            matched_policies=["balanced.high_impact.requires_draft"],
            requires_user_confirmation=True,
        )

    if write_intent.intent_type in AUTO_APPLY_TYPES:
        return PolicyDecision(
            run_id=write_intent.run_id,
            write_intent_id=write_intent.write_intent_id,
            decision=PolicyDecisionType.AUTO_APPLY,
            reasons=["Balanced policy allows this low-to-medium impact learning update."],
            matched_policies=["balanced.auto_apply"],
        )

    return PolicyDecision(
        run_id=write_intent.run_id,
        write_intent_id=write_intent.write_intent_id,
        decision=PolicyDecisionType.BLOCK,
        reasons=["No matching execution policy was found for this write intent."],
        matched_policies=["balanced.block_unknown"],
        overrideable=False,
    )

