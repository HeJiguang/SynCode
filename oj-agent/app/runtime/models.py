from typing import Any

from pydantic import BaseModel, Field

from app.runtime.enums import RiskLevel, RunStatus, TaskType


class RequestContext(BaseModel):
    """Immutable input context shared by every graph node."""

    trace_id: str
    user_id: str
    task_type: TaskType
    user_message: str
    conversation_id: str | None = None
    question_id: str | None = None
    question_title: str | None = None
    question_content: str | None = None
    user_code: str | None = None
    judge_result: str | None = None
    exam_id: str | None = None
    plan_id: str | None = None


class ExecutionState(BaseModel):
    """Runtime control metadata for the current graph execution."""

    run_id: str
    graph_name: str
    status: RunStatus
    active_node: str | None = None
    retry_count: int = 0
    branch_name: str | None = None
    fallback_type: str | None = None
    model_name: str | None = None


class EvidenceItem(BaseModel):
    """One retrieved evidence fragment used to ground the run."""

    evidence_id: str
    source_type: str
    source_id: str
    title: str | None = None
    snippet: str
    recall_score: float | None = None
    rerank_score: float | None = None
    trust_label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceState(BaseModel):
    """All evidence collected for the current run."""

    items: list[EvidenceItem] = Field(default_factory=list)
    route_names: list[str] = Field(default_factory=list)
    coverage_score: float | None = None


class GuardrailState(BaseModel):
    """Safety and completeness checks evaluated around the reasoning path."""

    risk_level: RiskLevel = RiskLevel.LOW
    completeness_ok: bool = False
    policy_ok: bool = True
    dirty_data_flags: list[str] = Field(default_factory=list)
    risk_reasons: list[str] = Field(default_factory=list)


class WriteIntent(BaseModel):
    """A graph-generated write proposal for Java-side execution."""

    intent_type: str
    target_service: str
    payload: dict[str, Any] = Field(default_factory=dict)


class OutcomeState(BaseModel):
    """User-visible output plus follow-up actions derived by the graph."""

    intent: str | None = None
    answer: str | None = None
    next_action: str | None = None
    confidence: float | None = None
    status_events: list[dict[str, str]] = Field(default_factory=list)
    response_payload: dict[str, Any] = Field(default_factory=dict)
    write_intents: list[WriteIntent] = Field(default_factory=list)


class UnifiedAgentState(BaseModel):
    """The single state object passed through the graph-native runtime."""

    request: RequestContext
    execution: ExecutionState
    evidence: EvidenceState
    guardrail: GuardrailState
    outcome: OutcomeState
