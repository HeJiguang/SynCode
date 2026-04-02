from app.graphs.capabilities.shared import CapabilitySupport
from app.graphs.capabilities.tutor_graph import build_tutor_graph
from app.guardrails.runtime import GuardrailOutput
from app.retrieval.models import RetrievalResult, RetrievedEvidence
from app.runtime.context import build_request_context
from app.runtime.enums import RiskLevel, RunStatus, TaskType
from app.runtime.models import EvidenceState, ExecutionState, GuardrailState, OutcomeState, UnifiedAgentState


def test_tutor_graph_populates_evidence_and_guardrail_state(monkeypatch):
    import app.graphs.capabilities.tutor_graph as tutor_module  # noqa: WPS433

    monkeypatch.setattr(
        tutor_module,
        "collect_capability_support",
        lambda request, *, query_fields: CapabilitySupport(
            retrieval=RetrievalResult(
                route_names=["lexical"],
                items=[
                    RetrievedEvidence(
                        evidence_id="lex-1",
                        route_name="lexical",
                        source_type="knowledge_doc",
                        source_id="doc-1",
                        title="Hash Map Patterns",
                        snippet="Use a hash map to track complements.",
                        score=0.93,
                    )
                ],
            ),
            request_guard=GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
            ),
            evidence_guard=GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
            ),
        ),
    )

    result = build_tutor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-tutor-001",
                user_id="u-1",
                task_type=TaskType.CHAT,
                user_message="Explain the core idea of this problem.",
                question_title="Two Sum",
                question_content="Find two numbers that add up to target.",
                user_code="public class Solution {}",
            ),
            "execution": ExecutionState(
                run_id="run-tutor-001",
                graph_name="supervisor_graph",
                status=RunStatus.RUNNING,
                active_node="chat_capability",
            ),
        }
    )

    state = result["unified_state"]

    assert state.evidence.route_names == ["lexical"]
    assert state.evidence.items
    assert state.guardrail.completeness_ok is True
    assert state.guardrail.policy_ok is True
    assert state.outcome.intent == "explain_problem"
    assert "Tutor summary:" in state.outcome.answer
    assert "Retrieved hint:" in state.outcome.answer


def test_tutor_graph_delegates_failure_intent_to_diagnose_graph(monkeypatch):
    import app.graphs.capabilities.tutor_graph as tutor_module  # noqa: WPS433

    class _StubDiagnoseGraph:
        def invoke(self, payload):
            request = payload["request"]
            execution = payload["execution"].model_copy(
                update={"status": RunStatus.SUCCEEDED, "active_node": "diagnose_graph"}
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
                        answer="DiagnoseGraph delegated answer",
                        confidence=0.93,
                        next_action="Trace the smallest failing sample.",
                    ),
                )
            }

    monkeypatch.setattr(tutor_module, "build_diagnose_graph", lambda: _StubDiagnoseGraph())

    result = build_tutor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-tutor-002",
                user_id="u-1",
                task_type=TaskType.CHAT,
                user_message="Why is this WA?",
                judge_result="WA on sample #2",
                user_code="public class Solution {}",
            ),
            "execution": ExecutionState(
                run_id="run-tutor-002",
                graph_name="supervisor_graph",
                status=RunStatus.RUNNING,
                active_node="chat_capability",
            ),
        }
    )

    state = result["unified_state"]

    assert state.outcome.answer == "DiagnoseGraph delegated answer"
    assert state.execution.active_node == "diagnose_graph"
    assert state.request.task_type is TaskType.DIAGNOSIS
    assert state.outcome.status_events[0]["node"] == "intent_router"


def test_tutor_graph_delegates_recommendation_intent_to_recommend_graph(monkeypatch):
    import app.graphs.capabilities.tutor_graph as tutor_module  # noqa: WPS433

    class _StubRecommendGraph:
        def invoke(self, payload):
            request = payload["request"]
            execution = payload["execution"].model_copy(
                update={"status": RunStatus.SUCCEEDED, "active_node": "recommend_graph"}
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
                        answer="RecommendGraph delegated answer",
                        confidence=0.89,
                        next_action="Start with one easier array problem.",
                    ),
                )
            }

    monkeypatch.setattr(tutor_module, "build_recommend_graph", lambda: _StubRecommendGraph())

    result = build_tutor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-tutor-003",
                user_id="u-1",
                task_type=TaskType.CHAT,
                user_message="What should I practice next?",
                question_title="Two Sum",
                question_content="Find two numbers that add up to target.",
            ),
            "execution": ExecutionState(
                run_id="run-tutor-003",
                graph_name="supervisor_graph",
                status=RunStatus.RUNNING,
                active_node="chat_capability",
            ),
        }
    )

    state = result["unified_state"]

    assert state.outcome.answer == "RecommendGraph delegated answer"
    assert state.execution.active_node == "recommend_graph"
    assert state.request.task_type is TaskType.RECOMMENDATION
    assert state.outcome.status_events[0]["node"] == "intent_router"


def test_tutor_graph_asks_for_context_when_workspace_context_is_missing():
    result = build_tutor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-tutor-004",
                user_id="u-1",
                task_type=TaskType.CHAT,
                user_message="Can you go deeper on that?",
            ),
            "execution": ExecutionState(
                run_id="run-tutor-004",
                graph_name="supervisor_graph",
                status=RunStatus.RUNNING,
                active_node="chat_capability",
            ),
        }
    )

    state = result["unified_state"]

    assert state.outcome.intent == "ask_for_context"
    assert state.guardrail.completeness_ok is False
    assert "workspace context" in state.guardrail.risk_reasons[0]
