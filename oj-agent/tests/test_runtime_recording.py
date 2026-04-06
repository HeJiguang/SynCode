from app.evaluation.store import evaluation_store
from app.observability.query_ledger import query_ledger
from app.observability.trace import trace_store
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


def setup_function():
    trace_store.clear()
    query_ledger.clear()
    evaluation_store.clear()


def test_execute_request_context_records_trace_query_and_eval_artifacts(monkeypatch):
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
            trace_id="trace-recording-001",
            user_id="u-1",
            task_type=TaskType.DIAGNOSIS,
            user_message="Why is this WA?",
            conversation_id="conv-recording-001",
            question_title="Two Sum",
            judge_result="WA on sample #2",
            user_code="public class Solution {}",
        ),
        {},
    )

    run = trace_store.get_run(state.execution.run_id)
    node_events = trace_store.list_node_events(state.execution.run_id)
    ledger_entries = query_ledger.list_entries()
    eval_records = evaluation_store.list_records()

    assert run.trace_id == "trace-recording-001"
    assert node_events
    assert any(event.node_name in {"llm_prepare", "llm_inference", "response_packaging"} for event in node_events)
    assert ledger_entries[-1].run_id == state.execution.run_id
    assert ledger_entries[-1].route_names == ["llm_only"]
    assert ledger_entries[-1].risk_level in {"low", "medium", "high"}
    assert eval_records[-1]["trace_id"] == "trace-recording-001"
    assert eval_records[-1]["task_type"] in {"chat", "diagnosis"}
