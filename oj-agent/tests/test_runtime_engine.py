from app.runtime.context import build_request_context
from app.runtime.engine import execute_request_context
from app.runtime.enums import RiskLevel, RunStatus, TaskType
from app.runtime.models import (
    EvidenceState,
    ExecutionState,
    GuardrailState,
    OutcomeState,
    UnifiedAgentState,
)


def test_execute_request_context_returns_llm_runtime_state(monkeypatch):
    import app.runtime.engine as engine_module  # noqa: WPS433

    monkeypatch.setattr(
        engine_module,
        "invoke_request_context",
        lambda request_context: UnifiedAgentState(
            request=request_context,
            execution=ExecutionState(
                run_id=request_context.trace_id,
                graph_name="llm_runtime",
                status=RunStatus.SUCCEEDED,
                active_node="response_packaging",
                model_name="deepseek-chat",
            ),
            evidence=EvidenceState(route_names=["llm_only"]),
            guardrail=GuardrailState(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
            ),
            outcome=OutcomeState(
                intent="analyze_failure",
                answer="请先检查哈希表更新时机。",
                next_action="先手推样例 [3,3]。",
                confidence=0.9,
                status_events=[
                    {"node": "llm_prepare", "message": "已整理大模型输入上下文。"},
                    {"node": "llm_inference", "message": "已完成推理。"},
                    {"node": "response_packaging", "message": "已整理模型输出结果。"},
                ],
            ),
        ),
    )

    state = execute_request_context(
        build_request_context(
            trace_id="trace-runtime-001",
            user_id="u-1",
            task_type=TaskType.DIAGNOSIS,
            user_message="Why is this WA?",
            conversation_id="conv-runtime-001",
            question_title="Two Sum",
            judge_result="WA on sample #2",
            user_code="public class Solution {}",
        ),
        {},
    )

    assert state.execution.graph_name == "llm_runtime"
    assert state.execution.status is RunStatus.SUCCEEDED
    assert state.outcome.intent == "analyze_failure"
    assert state.outcome.answer
    assert state.outcome.next_action
    assert state.outcome.status_events
