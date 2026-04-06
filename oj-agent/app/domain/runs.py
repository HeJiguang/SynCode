from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    """Return a UTC timestamp string for audit-friendly runtime records."""
    return datetime.now(timezone.utc).isoformat()


class RunType(str, Enum):
    INTERACTIVE_TUTOR = "interactive_tutor"
    INTERACTIVE_DIAGNOSIS = "interactive_diagnosis"
    INTERACTIVE_RECOMMENDATION = "interactive_recommendation"
    INTERACTIVE_PLAN = "interactive_plan"
    INTERACTIVE_REVIEW = "interactive_review"
    JUDGE_FOLLOWUP = "judge_followup"
    PROFILE_REFRESH = "profile_refresh"
    PLAN_RECOMPUTE = "plan_recompute"
    WEAKNESS_TRACKING = "weakness_tracking"
    MESSAGE_DELIVERY = "message_delivery"


class RunSource(str, Enum):
    WORKSPACE_PANEL = "workspace_panel"
    TRAINING_CENTER = "training_center"
    JUDGE_EVENT = "judge_event"
    SCHEDULER = "scheduler"
    ADMIN_TRIGGER = "admin_trigger"


class RunStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_USER = "WAITING_USER"
    APPLYING = "APPLYING"
    SUCCEEDED = "SUCCEEDED"
    PARTIALLY_APPLIED = "PARTIALLY_APPLIED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RunPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EventLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class EventType(str, Enum):
    RUN_ACCEPTED = "run.accepted"
    RUN_QUEUED = "run.queued"
    RUN_STARTED = "run.started"
    GRAPH_NODE_STARTED = "graph.node_started"
    GRAPH_NODE_COMPLETED = "graph.node_completed"
    RETRIEVAL_QUERY_PLANNED = "retrieval.query_planned"
    RETRIEVAL_EVIDENCE_READY = "retrieval.evidence_ready"
    TOOL_CALLED = "tool.called"
    TOOL_SUCCEEDED = "tool.succeeded"
    TOOL_FAILED = "tool.failed"
    GUARDRAIL_TRIGGERED = "guardrail.triggered"
    ARTIFACT_CREATED = "artifact.created"
    WRITE_INTENT_CREATED = "write.intent_created"
    WRITE_APPLIED = "write.applied"
    WRITE_BLOCKED = "write.blocked"
    DRAFT_CREATED = "draft.created"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"


class ContextRef(BaseModel):
    question_id: str | None = None
    submission_id: str | None = None
    exam_id: str | None = None
    training_plan_id: str | None = None
    weakness_snapshot_id: str | None = None


class Run(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run_{uuid4().hex}")
    run_type: RunType
    source: RunSource
    user_id: str
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid4().hex}")
    conversation_id: str | None = None
    status: RunStatus = RunStatus.ACCEPTED
    entry_graph: str = "llm_runtime"
    active_node: str | None = None
    priority: RunPriority = RunPriority.MEDIUM
    context_ref: ContextRef = Field(default_factory=ContextRef)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None


class RunEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    run_id: str
    seq: int
    event_type: EventType
    level: EventLevel = EventLevel.INFO
    timestamp: str = Field(default_factory=utc_now_iso)
    payload: dict[str, Any] = Field(default_factory=dict)
