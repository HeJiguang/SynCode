from app.evaluation.store import evaluation_store
from app.observability.query_ledger import query_ledger
from app.observability.trace import trace_store
from app.runtime.engine import execute_chat_request
from app.runtime.enums import RiskLevel, RunStatus, TaskType
from app.runtime.models import (
    EvidenceState,
    ExecutionState,
    GuardrailState,
    OutcomeState,
    RequestContext,
    UnifiedAgentState,
)
from app.runtime.streaming import stream_chat_request
from app.schemas.chat_request import ChatRequest


def setup_function():
    trace_store.clear()
    query_ledger.clear()
    evaluation_store.clear()


def test_execute_chat_request_records_trace_query_and_eval_artifacts():
    state = execute_chat_request(
        ChatRequest(
            trace_id="trace-recording-001",
            user_id="u-1",
            conversation_id="conv-recording-001",
            question_title="Two Sum",
            judge_result="WA on sample #2",
            user_code="public class Solution {}",
            user_message="Why is this WA?",
        ),
        {
            "X-User-Id": "u-1",
        },
    )

    run = trace_store.get_run(state.execution.run_id)
    node_events = trace_store.list_node_events(state.execution.run_id)
    ledger_entries = query_ledger.list_entries()
    eval_records = evaluation_store.list_records()

    assert run.trace_id == "trace-recording-001"
    assert node_events
    assert any(event.node_name in {"tutor_graph", "diagnose_graph"} for event in node_events)
    assert ledger_entries[-1].run_id == state.execution.run_id
    assert ledger_entries[-1].route_names
    assert ledger_entries[-1].risk_level in {"low", "medium", "high"}
    assert eval_records[-1]["trace_id"] == "trace-recording-001"
    assert eval_records[-1]["task_type"] in {"chat", "diagnosis"}


def test_stream_chat_request_records_trace_query_and_eval_artifacts(monkeypatch):
    import app.runtime.streaming as streaming_module  # noqa: WPS433

    monkeypatch.setattr(
        streaming_module,
        "prepare_chat_stream_state",
        lambda request, headers: UnifiedAgentState(
            request=RequestContext(
                trace_id="trace-stream-recording-001",
                user_id="u-1",
                task_type=TaskType.CHAT,
                user_message=request.user_message or "Help me look.",
            ),
            execution=ExecutionState(
                run_id="run-stream-recording-001",
                graph_name="supervisor_graph",
                status=RunStatus.SUCCEEDED,
                active_node="tutor_graph",
            ),
            evidence=EvidenceState(route_names=["lexical"]),
            guardrail=GuardrailState(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
            ),
            outcome=OutcomeState(
                intent="analyze_failure",
                confidence=0.88,
                next_action="Trace the failing sample.",
                status_events=[
                    {"node": "tutor_graph", "message": "Prepared streaming state."},
                ],
                response_payload={
                    "assistant_state": {
                        "intent": "analyze_failure",
                        "confidence": 0.88,
                        "next_action": "Trace the failing sample.",
                        "user_message": request.user_message,
                    }
                },
            ),
        ),
    )
    monkeypatch.setattr(
        streaming_module.chat_assistant,
        "stream_chat_answer",
        lambda state: iter(["Hel", "lo"]),
    )

    events = list(
        stream_chat_request(
            ChatRequest(
                trace_id="trace-stream-recording-001",
                user_id="u-1",
                question_title="Two Sum",
                user_message="Help me look.",
            ),
            {
                "X-User-Id": "u-1",
            },
        )
    )

    run = trace_store.get_run("run-stream-recording-001")
    node_events = trace_store.list_node_events("run-stream-recording-001")
    ledger_entries = query_ledger.list_entries()
    eval_records = evaluation_store.list_records()

    assert any("event: delta" in event for event in events)
    assert any("event: final" in event for event in events)
    assert run.trace_id == "trace-stream-recording-001"
    assert any(event.node_name == "tutor_graph" for event in node_events)
    assert ledger_entries[-1].run_id == "run-stream-recording-001"
    assert eval_records[-1]["trace_id"] == "trace-stream-recording-001"


def test_stream_chat_request_uses_existing_phase2_answer_without_llm_stream(monkeypatch):
    import app.runtime.streaming as streaming_module  # noqa: WPS433

    monkeypatch.setattr(
        streaming_module,
        "prepare_chat_stream_state",
        lambda request, headers: UnifiedAgentState(
            request=RequestContext(
                trace_id="trace-stream-phase2-001",
                user_id="u-1",
                task_type=TaskType.REVIEW,
                user_message=request.user_message or "Summarize my recent practice.",
            ),
            execution=ExecutionState(
                run_id="run-stream-phase2-001",
                graph_name="supervisor_graph",
                status=RunStatus.SUCCEEDED,
                active_node="review_graph",
            ),
            evidence=EvidenceState(route_names=["review"]),
            guardrail=GuardrailState(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
            ),
            outcome=OutcomeState(
                intent="review_summary",
                answer="Review summary:\nFocus on edge-case review before increasing difficulty.",
                confidence=0.84,
                next_action="Review your last two wrong answers before starting new problems.",
                status_events=[
                    {"node": "review_graph", "message": "Prepared phase 2 review state."},
                ],
                response_payload={},
            ),
        ),
    )

    def _unexpected_llm_call(*args, **kwargs):
        raise AssertionError("phase 2 streaming path should not call chat assistant")

    monkeypatch.setattr(streaming_module.chat_assistant, "stream_chat_answer", _unexpected_llm_call)
    monkeypatch.setattr(streaming_module.chat_assistant, "generate_chat_answer", _unexpected_llm_call)

    events = list(
        stream_chat_request(
            ChatRequest(
                trace_id="trace-stream-phase2-001",
                user_id="u-1",
                user_message="Summarize my recent practice.",
            ),
            {
                "X-User-Id": "u-1",
            },
        )
    )

    assert not any("event: delta" in event for event in events)
    assert any("event: final" in event for event in events)
    assert any("Review summary:" in event for event in events)
