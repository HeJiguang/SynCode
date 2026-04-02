from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from app.graphs.capabilities.diagnose_graph import build_diagnose_graph
from app.graphs.capabilities.recommend_graph import build_recommend_graph
from app.graphs.capabilities.shared import (
    CapabilitySupport,
    build_evidence_state,
    build_guardrail_state,
    collect_capability_support,
    update_execution,
)
from app.runtime.enums import RiskLevel, RunStatus, TaskType
from app.runtime.models import EvidenceState, GuardrailState, OutcomeState, UnifiedAgentState


ASK_FOR_CONTEXT = "ask_for_context"
EXPLAIN_PROBLEM = "explain_problem"
ANALYZE_FAILURE = "analyze_failure"
RECOMMEND_QUESTION = "recommend_question"


class TutorGraphState(TypedDict):
    request: object
    execution: object
    intent: NotRequired[str]
    support: NotRequired[CapabilitySupport]
    unified_state: UnifiedAgentState


def route_intent_node(state: TutorGraphState) -> TutorGraphState:
    request = state["request"]
    return {
        **state,
        "intent": _interactive_intent(request),
    }


def route_after_intent(state: TutorGraphState) -> str:
    return state["intent"]


def collect_support_node(state: TutorGraphState) -> TutorGraphState:
    return {
        **state,
        "support": collect_capability_support(
            state["request"],
            query_fields=(
                "question_title",
                "question_content",
                "judge_result",
                "user_message",
            ),
        ),
    }


def ask_for_context_node(state: TutorGraphState) -> TutorGraphState:
    request = state["request"]
    unified_state = UnifiedAgentState(
        request=request,
        execution=update_execution(state["execution"], active_node="tutor_context_gate"),
        evidence=EvidenceState(),
        guardrail=GuardrailState(
            risk_level=RiskLevel.MEDIUM,
            completeness_ok=False,
            policy_ok=True,
            risk_reasons=["missing workspace context for tutor answer"],
        ),
        outcome=OutcomeState(
            intent=ASK_FOR_CONTEXT,
            answer="I need the problem statement, your current code, or the latest judge result before I can give a grounded answer.",
            confidence=0.25,
            next_action="Send the current question context and the latest failing submission details.",
            status_events=[
                {"node": "intent_router", "message": "The request needs more workspace context before tutoring can continue."}
            ],
        ),
    )
    return {**state, "unified_state": unified_state}


def tutor_reasoning_node(state: TutorGraphState) -> TutorGraphState:
    request = state["request"]
    support = state["support"]
    retrieval = support.retrieval
    strongest_evidence = retrieval.items[0] if retrieval.items else None

    answer_lines = ["Tutor summary:"]
    if request.question_title:
        answer_lines.append(f"Anchor the reasoning around {request.question_title}.")
    if request.question_content:
        answer_lines.append("Restate the input/output contract and identify the invariant that must remain true after each step.")
    else:
        answer_lines.append("Start by restating the invariant you expect to maintain through the solution.")
    if request.user_code:
        answer_lines.append("Compare your current code against that invariant before changing syntax or data structures.")
    if request.judge_result:
        answer_lines.append(f"Use the latest judge signal as a filter: {request.judge_result}.")
    if strongest_evidence is not None:
        answer_lines.append(f"Retrieved hint: {strongest_evidence.snippet}")
    answer_lines.append("Do not jump to a rewrite until you can explain where the current state first diverges from the expected state.")

    next_action = (
        "Dry-run the smallest non-trivial sample and write down the expected state after each update."
        if request.user_code or request.judge_result
        else "Write the invariant in one sentence before coding the next attempt."
    )

    unified_state = UnifiedAgentState(
        request=request,
        execution=update_execution(state["execution"], active_node="interactive_learning_graph"),
        evidence=build_evidence_state(retrieval),
        guardrail=build_guardrail_state(support.request_guard, support.evidence_guard),
        outcome=OutcomeState(
            intent=EXPLAIN_PROBLEM,
            answer="\n".join(answer_lines),
            confidence=0.82 if retrieval.items else 0.7,
            next_action=next_action,
            status_events=[
                {"node": "intent_router", "message": "Routed request to the tutor reasoning path."},
                {"node": "retrieval_runtime", "message": "Collected learning evidence for the workspace prompt."},
                {"node": "reasoner_node", "message": "Built a tutor explanation from workspace context and retrieved evidence."},
                {"node": "composer_node", "message": "Composed the final tutor answer and next step."},
            ],
        ),
    )
    return {**state, "unified_state": unified_state}


def delegate_diagnosis_node(state: TutorGraphState) -> TutorGraphState:
    request = state["request"].model_copy(update={"task_type": TaskType.DIAGNOSIS})
    delegated = build_diagnose_graph().invoke(
        {
            "request": request,
            "execution": state["execution"],
        }
    )["unified_state"]
    return {
        **state,
        "unified_state": _prepend_status_event(
            delegated,
            {"node": "intent_router", "message": "Routed chat request to the diagnosis capability."},
        ),
    }


def delegate_recommendation_node(state: TutorGraphState) -> TutorGraphState:
    request = state["request"].model_copy(update={"task_type": TaskType.RECOMMENDATION})
    delegated = build_recommend_graph().invoke(
        {
            "request": request,
            "execution": state["execution"],
        }
    )["unified_state"]
    return {
        **state,
        "unified_state": _prepend_status_event(
            delegated,
            {"node": "intent_router", "message": "Routed chat request to the recommendation capability."},
        ),
    }


def _interactive_intent(request) -> str:
    message = (request.user_message or "").casefold()
    has_workspace_context = any(
        [
            request.question_title,
            request.question_content,
            request.user_code,
            request.judge_result,
        ]
    )

    recommendation_keywords = [
        "practice next",
        "next practice",
        "recommend",
        "next step",
        "what should i practice",
    ]
    diagnosis_keywords = [
        "wa",
        "tle",
        "wrong answer",
        "still wrong",
        "why is this",
        "why does this fail",
        "diagnose",
        "latest submission",
    ]

    if any(keyword in message for keyword in recommendation_keywords):
        return RECOMMEND_QUESTION
    judge_signal = (request.judge_result or "").casefold()
    if request.judge_result or any(keyword in message for keyword in diagnosis_keywords) or any(
        signal in judge_signal for signal in (" re ", " ce ", "runtime error", "compile error")
    ):
        return ANALYZE_FAILURE
    if not has_workspace_context:
        return ASK_FOR_CONTEXT
    return EXPLAIN_PROBLEM


def _prepend_status_event(state: UnifiedAgentState, event: dict[str, str]) -> UnifiedAgentState:
    return state.model_copy(
        update={
            "outcome": state.outcome.model_copy(
                update={"status_events": [event, *state.outcome.status_events]}
            )
        }
    )


def build_tutor_graph():
    graph = StateGraph(TutorGraphState)
    graph.add_node("route_intent", route_intent_node)
    graph.add_node("collect_support", collect_support_node)
    graph.add_node("tutor_reasoning", tutor_reasoning_node)
    graph.add_node("ask_for_context", ask_for_context_node)
    graph.add_node("delegate_diagnosis", delegate_diagnosis_node)
    graph.add_node("delegate_recommendation", delegate_recommendation_node)

    graph.add_edge(START, "route_intent")
    graph.add_conditional_edges(
        "route_intent",
        route_after_intent,
        {
            ASK_FOR_CONTEXT: "ask_for_context",
            EXPLAIN_PROBLEM: "collect_support",
            ANALYZE_FAILURE: "delegate_diagnosis",
            RECOMMEND_QUESTION: "delegate_recommendation",
        },
    )
    graph.add_edge("collect_support", "tutor_reasoning")
    graph.add_edge("tutor_reasoning", END)
    graph.add_edge("ask_for_context", END)
    graph.add_edge("delegate_diagnosis", END)
    graph.add_edge("delegate_recommendation", END)
    return graph.compile()
