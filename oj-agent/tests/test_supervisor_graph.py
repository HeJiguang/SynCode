from app.graphs.supervisor_graph import build_supervisor_graph
from app.runtime.context import build_request_context
from app.runtime.enums import RiskLevel, RunStatus, TaskType
from app.runtime.models import (
    EvidenceState,
    ExecutionState,
    GuardrailState,
    OutcomeState,
    UnifiedAgentState,
)


def test_supervisor_graph_routes_chat_requests_to_tutor_graph(monkeypatch):
    import app.graphs.supervisor_graph as supervisor_module  # noqa: WPS433

    class _StubTutorGraph:
        def invoke(self, payload):
            request = payload["request"]
            execution = payload["execution"].model_copy(
                update={
                    "status": RunStatus.SUCCEEDED,
                    "active_node": "tutor_graph",
                }
            )
            return {
                "unified_state": UnifiedAgentState(
                    request=request,
                    execution=execution,
                    evidence=EvidenceState(route_names=["stub"]),
                    guardrail=GuardrailState(
                        risk_level=RiskLevel.LOW,
                        completeness_ok=True,
                        policy_ok=True,
                    ),
                    outcome=OutcomeState(
                        intent="analyze_failure",
                        answer="Tutor graph answer",
                        confidence=0.9,
                        next_action="Trace the failing path.",
                    ),
                )
            }

    monkeypatch.setattr(supervisor_module, "build_tutor_graph", lambda: _StubTutorGraph())

    result = build_supervisor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-supervisor-001",
                user_id="u-1",
                task_type=TaskType.CHAT,
                user_message="Explain the core idea of this problem.",
            )
        }
    )

    assert result["unified_state"].outcome.answer == "Tutor graph answer"
    assert result["unified_state"].execution.active_node == "tutor_graph"


def test_supervisor_graph_routes_diagnosis_requests_to_diagnose_graph(monkeypatch):
    import app.graphs.supervisor_graph as supervisor_module  # noqa: WPS433

    class _StubDiagnoseGraph:
        def invoke(self, payload):
            request = payload["request"]
            execution = payload["execution"].model_copy(
                update={
                    "status": RunStatus.SUCCEEDED,
                    "active_node": "diagnose_graph",
                }
            )
            return {
                "unified_state": UnifiedAgentState(
                    request=request,
                    execution=execution,
                    evidence=EvidenceState(route_names=["diagnosis"]),
                    guardrail=GuardrailState(
                        risk_level=RiskLevel.LOW,
                        completeness_ok=True,
                        policy_ok=True,
                    ),
                    outcome=OutcomeState(
                        intent="analyze_failure",
                        answer="Diagnose graph answer",
                        confidence=0.92,
                        next_action="Trace the smallest failing input.",
                    ),
                )
            }

    monkeypatch.setattr(supervisor_module, "build_diagnose_graph", lambda: _StubDiagnoseGraph())

    result = build_supervisor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-supervisor-002",
                user_id="u-1",
                task_type=TaskType.DIAGNOSIS,
                user_message="Why is this WA?",
                question_title="Two Sum",
                judge_result="WA on sample #2",
                user_code="public class Solution {}",
            )
        }
    )

    assert result["unified_state"].outcome.answer == "Diagnose graph answer"
    assert result["unified_state"].execution.active_node == "diagnose_graph"


def test_supervisor_graph_routes_recommendation_requests_to_recommend_graph(monkeypatch):
    import app.graphs.supervisor_graph as supervisor_module  # noqa: WPS433

    class _StubRecommendGraph:
        def invoke(self, payload):
            request = payload["request"]
            execution = payload["execution"].model_copy(
                update={
                    "status": RunStatus.SUCCEEDED,
                    "active_node": "recommend_graph",
                }
            )
            return {
                "unified_state": UnifiedAgentState(
                    request=request,
                    execution=execution,
                    evidence=EvidenceState(route_names=["recommendation"]),
                    guardrail=GuardrailState(
                        risk_level=RiskLevel.LOW,
                        completeness_ok=True,
                        policy_ok=True,
                    ),
                    outcome=OutcomeState(
                        intent="recommend_question",
                        answer="Recommend graph answer",
                        confidence=0.88,
                        next_action="Start with one easier array problem.",
                    ),
                )
            }

    monkeypatch.setattr(supervisor_module, "build_recommend_graph", lambda: _StubRecommendGraph())

    result = build_supervisor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-supervisor-003",
                user_id="u-1",
                task_type=TaskType.RECOMMENDATION,
                user_message="What should I practice next?",
                question_title="Two Sum",
            )
        }
    )

    assert result["unified_state"].outcome.answer == "Recommend graph answer"
    assert result["unified_state"].execution.active_node == "recommend_graph"


def test_supervisor_graph_routes_review_requests_to_review_graph(monkeypatch):
    import app.graphs.supervisor_graph as supervisor_module  # noqa: WPS433

    class _StubReviewGraph:
        def invoke(self, payload):
            request = payload["request"]
            execution = payload["execution"].model_copy(
                update={
                    "status": RunStatus.SUCCEEDED,
                    "active_node": "review_graph",
                }
            )
            return {
                "unified_state": UnifiedAgentState(
                    request=request,
                    execution=execution,
                    evidence=EvidenceState(route_names=["review"]),
                    guardrail=GuardrailState(
                        risk_level=RiskLevel.LOW,
                        completeness_ok=True,
                        policy_ok=True,
                    ),
                    outcome=OutcomeState(
                        intent="review_summary",
                        answer="Review graph answer",
                        confidence=0.83,
                        next_action="Start the next cycle with boundary-case review.",
                    ),
                )
            }

    monkeypatch.setattr(supervisor_module, "build_review_graph", lambda: _StubReviewGraph())

    result = build_supervisor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-supervisor-004",
                user_id="u-1",
                task_type=TaskType.REVIEW,
                user_message="Summarize my recent practice.",
            )
        }
    )

    assert result["unified_state"].outcome.answer == "Review graph answer"
    assert result["unified_state"].execution.active_node == "review_graph"


def test_supervisor_graph_routes_profile_requests_to_profile_graph(monkeypatch):
    import app.graphs.supervisor_graph as supervisor_module  # noqa: WPS433

    class _StubProfileGraph:
        def invoke(self, payload):
            request = payload["request"]
            execution = payload["execution"].model_copy(
                update={
                    "status": RunStatus.SUCCEEDED,
                    "active_node": "profile_graph",
                }
            )
            return {
                "unified_state": UnifiedAgentState(
                    request=request,
                    execution=execution,
                    evidence=EvidenceState(route_names=["profile"]),
                    guardrail=GuardrailState(
                        risk_level=RiskLevel.LOW,
                        completeness_ok=True,
                        policy_ok=True,
                    ),
                    outcome=OutcomeState(
                        intent="profile_update",
                        confidence=0.84,
                        response_payload={"focus_tags": ["array", "hash map"]},
                    ),
                )
            }

    monkeypatch.setattr(supervisor_module, "build_profile_graph", lambda: _StubProfileGraph())

    result = build_supervisor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-supervisor-005",
                user_id="u-1",
                task_type=TaskType.PROFILE,
                user_message="Update my profile.",
            )
        }
    )

    assert result["unified_state"].outcome.intent == "profile_update"
    assert result["unified_state"].execution.active_node == "profile_graph"


def test_supervisor_graph_infers_review_capability_from_chat_request(monkeypatch):
    import app.graphs.supervisor_graph as supervisor_module  # noqa: WPS433

    class _StubReviewGraph:
        def invoke(self, payload):
            request = payload["request"]
            execution = payload["execution"].model_copy(
                update={
                    "status": RunStatus.SUCCEEDED,
                    "active_node": "review_graph",
                }
            )
            return {
                "unified_state": UnifiedAgentState(
                    request=request,
                    execution=execution,
                    evidence=EvidenceState(route_names=["review"]),
                    guardrail=GuardrailState(
                        risk_level=RiskLevel.LOW,
                        completeness_ok=True,
                        policy_ok=True,
                    ),
                    outcome=OutcomeState(
                        intent="review_summary",
                        answer="Review graph answer",
                        confidence=0.83,
                        next_action="Start the next cycle with boundary-case review.",
                    ),
                )
            }

    monkeypatch.setattr(supervisor_module, "build_review_graph", lambda: _StubReviewGraph())

    result = build_supervisor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-supervisor-006",
                user_id="u-1",
                task_type=TaskType.CHAT,
                user_message="Summarize my recent practice and mistakes.",
            )
        }
    )

    assert result["unified_state"].outcome.intent == "review_summary"
    assert result["unified_state"].execution.active_node == "review_graph"
    assert result["unified_state"].request.task_type is TaskType.REVIEW


def test_supervisor_graph_infers_profile_capability_from_chat_request(monkeypatch):
    import app.graphs.supervisor_graph as supervisor_module  # noqa: WPS433

    class _StubProfileGraph:
        def invoke(self, payload):
            request = payload["request"]
            execution = payload["execution"].model_copy(
                update={
                    "status": RunStatus.SUCCEEDED,
                    "active_node": "profile_graph",
                }
            )
            return {
                "unified_state": UnifiedAgentState(
                    request=request,
                    execution=execution,
                    evidence=EvidenceState(route_names=["profile"]),
                    guardrail=GuardrailState(
                        risk_level=RiskLevel.LOW,
                        completeness_ok=True,
                        policy_ok=True,
                    ),
                    outcome=OutcomeState(
                        intent="profile_update",
                        answer="Profile graph answer",
                        confidence=0.84,
                        next_action="Review the updated focus tags.",
                        response_payload={"focus_tags": ["array", "hash map"]},
                    ),
                )
            }

    monkeypatch.setattr(supervisor_module, "build_profile_graph", lambda: _StubProfileGraph())

    result = build_supervisor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-supervisor-007",
                user_id="u-1",
                task_type=TaskType.CHAT,
                user_message="Update my learning profile based on recent submissions.",
            )
        }
    )

    assert result["unified_state"].outcome.intent == "profile_update"
    assert result["unified_state"].execution.active_node == "profile_graph"
    assert result["unified_state"].request.task_type is TaskType.PROFILE
