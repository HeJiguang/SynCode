from app.evaluation.store import evaluation_store
from app.observability.query_ledger import query_ledger
from app.observability.trace import trace_store
from app.runtime.context import build_request_context
from app.runtime.engine import execute_request_context
from app.runtime.enums import TaskType


def setup_function():
    trace_store.clear()
    query_ledger.clear()
    evaluation_store.clear()


def test_execute_request_context_records_trace_query_and_eval_artifacts():
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
    assert any(event.node_name in {"tutor_graph", "diagnose_graph"} for event in node_events)
    assert ledger_entries[-1].run_id == state.execution.run_id
    assert ledger_entries[-1].route_names
    assert ledger_entries[-1].risk_level in {"low", "medium", "high"}
    assert eval_records[-1]["trace_id"] == "trace-recording-001"
    assert eval_records[-1]["task_type"] in {"chat", "diagnosis"}
