from app.graphs.capabilities.tutor_graph import build_tutor_graph
from app.runtime.context import build_request_context
from app.runtime.enums import RiskLevel, RunStatus, TaskType
from app.runtime.models import ExecutionState


def test_tutor_graph_populates_evidence_and_guardrail_state(monkeypatch):
    import app.graphs.capabilities.tutor_graph as tutor_module  # noqa: WPS433
    from app.retrieval.models import RetrievalResult, RetrievedEvidence  # noqa: WPS433

    class _StubRetrievalRuntime:
        def retrieve(self, query):
            return RetrievalResult(
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
            )

    class _StubGuardrailRuntime:
        def evaluate(self, guardrail_input):
            from app.guardrails.runtime import GuardrailOutput  # noqa: WPS433

            return GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=[],
            )

        def evaluate_output(self, *, answer, evidence_count):
            from app.guardrails.runtime import GuardrailOutput  # noqa: WPS433

            return GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=[],
            )

    class _StubLegacyGraph:
        def invoke(self, payload):
            return {
                "intent": "explain_problem",
                "status_events": [
                    {"node": "router", "message": "Routed request to intent: explain_problem."}
                ],
                "knowledge_hits": [],
                "context_gaps": [],
                "confidence": 0.88,
                "next_action": "Trace the smallest failing sample.",
                "final_answer": "Legacy answer",
            }

    monkeypatch.setattr(tutor_module, "RetrievalRuntime", lambda: _StubRetrievalRuntime())
    monkeypatch.setattr(tutor_module, "GuardrailRuntime", lambda: _StubGuardrailRuntime())
    monkeypatch.setattr(tutor_module, "build_graph", lambda: _StubLegacyGraph())
    monkeypatch.setattr(
        tutor_module.chat_assistant,
        "generate_chat_answer",
        lambda state: (
            "TutorGraph answer",
            0.91,
            "Trace the smallest failing sample.",
            "mock-model",
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
                judge_result="WA on sample #2",
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
    assert state.evidence.items[0].source_id == "doc-1"
    assert state.guardrail.completeness_ok is True
    assert state.guardrail.policy_ok is True
    assert state.outcome.answer == "TutorGraph answer"


def test_tutor_graph_delegates_failure_intent_to_diagnose_graph(monkeypatch):
    import app.graphs.capabilities.tutor_graph as tutor_module  # noqa: WPS433
    from app.retrieval.models import RetrievalResult  # noqa: WPS433
    from app.runtime.models import (  # noqa: WPS433
        EvidenceState,
        GuardrailState,
        OutcomeState,
        UnifiedAgentState,
    )

    class _StubRetrievalRuntime:
        def retrieve(self, query):
            return RetrievalResult(route_names=[], items=[])

    class _StubGuardrailRuntime:
        def evaluate(self, guardrail_input):
            from app.guardrails.runtime import GuardrailOutput  # noqa: WPS433

            return GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=[],
                triggered_verifiers=["request_verifier"],
            )

        def evaluate_output(self, *, answer, evidence_count):
            from app.guardrails.runtime import GuardrailOutput  # noqa: WPS433

            return GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=[],
                triggered_verifiers=["output_verifier"],
            )

    class _StubLegacyGraph:
        def invoke(self, payload):
            return {
                "intent": "analyze_failure",
                "question_title": "Two Sum",
                "judge_result": "WA on sample #2",
                "user_code": "public class Solution {}",
                "user_message": "Why is this WA?",
                "status_events": [
                    {"node": "router", "message": "Routed request to intent: analyze_failure."}
                ],
                "final_answer": "Legacy answer",
                "confidence": 0.88,
                "next_action": "Trace the smallest failing sample.",
            }

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

    monkeypatch.setattr(tutor_module, "RetrievalRuntime", lambda: _StubRetrievalRuntime())
    monkeypatch.setattr(tutor_module, "GuardrailRuntime", lambda: _StubGuardrailRuntime())
    monkeypatch.setattr(tutor_module, "build_graph", lambda: _StubLegacyGraph())
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


def test_tutor_graph_delegates_recommendation_intent_to_recommend_graph(monkeypatch):
    import app.graphs.capabilities.tutor_graph as tutor_module  # noqa: WPS433
    from app.retrieval.models import RetrievalResult  # noqa: WPS433
    from app.runtime.models import (  # noqa: WPS433
        EvidenceState,
        GuardrailState,
        OutcomeState,
        UnifiedAgentState,
    )

    class _StubRetrievalRuntime:
        def retrieve(self, query):
            return RetrievalResult(route_names=[], items=[])

    class _StubGuardrailRuntime:
        def evaluate(self, guardrail_input):
            from app.guardrails.runtime import GuardrailOutput  # noqa: WPS433

            return GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=[],
                triggered_verifiers=["request_verifier"],
            )

        def evaluate_output(self, *, answer, evidence_count):
            from app.guardrails.runtime import GuardrailOutput  # noqa: WPS433

            return GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=[],
                triggered_verifiers=["output_verifier"],
            )

    class _StubLegacyGraph:
        def invoke(self, payload):
            return {
                "intent": "recommend_question",
                "question_title": "Two Sum",
                "question_content": "Find two numbers that add up to target.",
                "user_message": "What should I practice next?",
                "status_events": [
                    {"node": "router", "message": "Routed request to intent: recommend_question."}
                ],
                "final_answer": "Legacy answer",
                "confidence": 0.81,
                "next_action": "Practice another array problem.",
            }

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

    monkeypatch.setattr(tutor_module, "RetrievalRuntime", lambda: _StubRetrievalRuntime())
    monkeypatch.setattr(tutor_module, "GuardrailRuntime", lambda: _StubGuardrailRuntime())
    monkeypatch.setattr(tutor_module, "build_graph", lambda: _StubLegacyGraph())
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


def test_tutor_graph_merges_evidence_guard_for_low_evidence(monkeypatch):
    import app.graphs.capabilities.tutor_graph as tutor_module  # noqa: WPS433
    from app.retrieval.models import RetrievalResult  # noqa: WPS433

    class _StubRetrievalRuntime:
        def retrieve(self, query):
            return RetrievalResult(route_names=[], items=[])

    class _StubGuardrailRuntime:
        def evaluate(self, guardrail_input):
            from app.guardrails.runtime import GuardrailOutput  # noqa: WPS433

            return GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=[],
                triggered_verifiers=["request_verifier"],
            )

        def evaluate_evidence(self, *, task_type, evidence_count):
            from app.guardrails.runtime import GuardrailOutput  # noqa: WPS433

            return GuardrailOutput(
                risk_level=RiskLevel.MEDIUM,
                completeness_ok=False,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=["Insufficient evidence for grounded tutor answer."],
                triggered_verifiers=["evidence_verifier"],
            )

        def evaluate_output(self, *, answer, evidence_count):
            from app.guardrails.runtime import GuardrailOutput  # noqa: WPS433

            return GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=[],
                triggered_verifiers=["output_verifier"],
            )

    class _StubLegacyGraph:
        def invoke(self, payload):
            return {
                "intent": "explain_problem",
                "status_events": [
                    {"node": "router", "message": "Routed request to intent: explain_problem."}
                ],
                "knowledge_hits": [],
                "context_gaps": [],
                "confidence": 0.66,
                "next_action": "Share the failing example.",
                "final_answer": "Legacy answer",
            }

    monkeypatch.setattr(tutor_module, "RetrievalRuntime", lambda: _StubRetrievalRuntime())
    monkeypatch.setattr(tutor_module, "GuardrailRuntime", lambda: _StubGuardrailRuntime())
    monkeypatch.setattr(tutor_module, "build_graph", lambda: _StubLegacyGraph())
    monkeypatch.setattr(
        tutor_module.chat_assistant,
        "generate_chat_answer",
        lambda state: (
            "TutorGraph answer",
            0.82,
            "Share the failing example.",
            "mock-model",
        ),
    )

    result = build_tutor_graph().invoke(
        {
            "request": build_request_context(
                trace_id="trace-tutor-004",
                user_id="u-1",
                task_type=TaskType.CHAT,
                user_message="Explain the likely bug here.",
                question_title="Two Sum",
                user_code="public class Solution {}",
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

    assert state.guardrail.risk_level is RiskLevel.MEDIUM
    assert state.guardrail.completeness_ok is False
    assert "Insufficient evidence for grounded tutor answer." in state.guardrail.risk_reasons
