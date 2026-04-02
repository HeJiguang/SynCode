from app.runtime.context import build_request_context
from app.runtime.engine import execute_request_context
from app.runtime.enums import RunStatus, TaskType


def test_execute_request_context_returns_unified_agent_state():
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

    assert state.execution.graph_name == "supervisor_graph"
    assert state.execution.status is RunStatus.SUCCEEDED
    assert state.outcome.intent == "analyze_failure"
    assert state.outcome.answer
    assert state.outcome.next_action
    assert state.outcome.status_events
