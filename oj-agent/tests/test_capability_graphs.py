from app.graphs.capabilities.diagnose_graph import build_diagnose_graph
from app.graphs.capabilities.plan_graph import build_plan_graph
from app.graphs.capabilities.profile_graph import build_profile_graph
from app.graphs.capabilities.recommend_graph import build_recommend_graph
from app.graphs.capabilities.review_graph import build_review_graph
from app.graphs.capabilities.tutor_graph import build_tutor_graph
from app.runtime.context import build_request_context
from app.runtime.enums import RunStatus, TaskType
from app.runtime.models import ExecutionState


def test_capability_graph_builders_return_compiled_graphs():
    graphs = [
        build_tutor_graph(),
        build_diagnose_graph(),
        build_recommend_graph(),
        build_plan_graph(),
        build_review_graph(),
        build_profile_graph(),
    ]

    assert all(graph is not None for graph in graphs)
    assert all(hasattr(graph, "invoke") for graph in graphs)


def test_diagnose_graph_returns_structured_unified_state():
    result = build_diagnose_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-diagnose-001",
                user_id="u-1",
                task_type=TaskType.DIAGNOSIS,
                user_message="Why is this WA?",
                question_title="Two Sum",
                judge_result="WA on sample #2",
                user_code="public class Solution {}",
            ),
            "execution": ExecutionState(
                run_id="run-diagnose-001",
                graph_name="supervisor_graph",
                status=RunStatus.RUNNING,
                active_node="diagnose_capability",
            ),
        }
    )

    state = result["unified_state"]
    assert state.outcome.intent == "analyze_failure"
    assert state.outcome.answer
    assert state.outcome.next_action


def test_recommend_graph_returns_structured_unified_state():
    result = build_recommend_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-recommend-001",
                user_id="u-1",
                task_type=TaskType.RECOMMENDATION,
                user_message="What should I practice next?",
                question_title="Two Sum",
                question_content="Find two numbers that add up to target.",
            ),
            "execution": ExecutionState(
                run_id="run-recommend-001",
                graph_name="supervisor_graph",
                status=RunStatus.RUNNING,
                active_node="recommend_capability",
            ),
        }
    )

    state = result["unified_state"]
    assert state.outcome.intent == "recommend_question"
    assert state.outcome.answer
    assert state.outcome.next_action


def test_review_graph_returns_structured_unified_state():
    result = build_review_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-review-001",
                user_id="u-1",
                task_type=TaskType.REVIEW,
                user_message="Summarize my recent practice.",
                question_title="Two Sum",
            ),
            "execution": ExecutionState(
                run_id="run-review-001",
                graph_name="supervisor_graph",
                status=RunStatus.RUNNING,
                active_node="review_capability",
            ),
        }
    )

    state = result["unified_state"]
    assert state.outcome.intent == "review_summary"
    assert state.outcome.answer
    assert state.outcome.next_action


def test_profile_graph_returns_structured_unified_state():
    result = build_profile_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-profile-001",
                user_id="u-1",
                task_type=TaskType.PROFILE,
                user_message="Update my learning profile.",
                question_title="Two Sum",
            ),
            "execution": ExecutionState(
                run_id="run-profile-001",
                graph_name="supervisor_graph",
                status=RunStatus.RUNNING,
                active_node="profile_capability",
            ),
        }
    )

    state = result["unified_state"]
    assert state.outcome.intent == "profile_update"
    assert state.outcome.response_payload
    assert state.outcome.write_intents
