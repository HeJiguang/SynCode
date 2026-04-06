from app.evaluation.hooks import build_chat_eval_record, build_plan_eval_record
from app.runtime.context import build_request_context
from app.runtime.enums import RiskLevel, RunStatus, TaskType
from app.runtime.models import (
    EvidenceItem,
    EvidenceState,
    ExecutionState,
    GuardrailState,
    OutcomeState,
    UnifiedAgentState,
)


def _build_state(task_type: TaskType) -> UnifiedAgentState:
    return UnifiedAgentState(
        request=build_request_context(
            trace_id="trace-eval-001",
            user_id="u-1",
            task_type=task_type,
            user_message="Why is this WA?" if task_type is TaskType.CHAT else "Generate a training plan.",
            question_title="Two Sum",
            judge_result="WA on sample #2",
            user_code="class Solution {}",
        ),
        execution=ExecutionState(
            run_id="run-eval-001",
            graph_name="llm_runtime",
            status=RunStatus.SUCCEEDED,
            active_node="response_packaging" if task_type is TaskType.CHAT else "training_plan_llm",
        ),
        evidence=EvidenceState(
            items=[
                EvidenceItem(
                    evidence_id="ev-1",
                    source_type="knowledge_doc",
                    source_id="doc-1",
                    title="Hash Map Patterns",
                    snippet="Use a hash map to track complements.",
                    recall_score=0.9,
                )
            ],
            route_names=["llm_only"],
            coverage_score=1.0,
        ),
        guardrail=GuardrailState(
            risk_level=RiskLevel.LOW,
            completeness_ok=True,
            policy_ok=True,
        ),
        outcome=OutcomeState(
            intent="analyze_failure" if task_type is TaskType.CHAT else "training_plan",
            answer="Answer body" if task_type is TaskType.CHAT else None,
            next_action="Trace the failing sample.",
            confidence=0.91,
            status_events=[{"node": "response_packaging", "message": "Completed model response packaging."}],
        ),
    )


def test_build_chat_eval_record_contains_trace_and_evidence_summary():
    record = build_chat_eval_record(_build_state(TaskType.CHAT))

    assert record["trace_id"] == "trace-eval-001"
    assert record["task_type"] == "chat"
    assert record["evidence_count"] == 1
    assert record["guardrail_risk"] == "low"


def test_build_plan_eval_record_contains_plan_focused_summary():
    record = build_plan_eval_record(_build_state(TaskType.TRAINING_PLAN))

    assert record["trace_id"] == "trace-eval-001"
    assert record["task_type"] == "training_plan"
    assert record["graph_name"] == "llm_runtime"
    assert record["route_names"] == ["llm_only"]
