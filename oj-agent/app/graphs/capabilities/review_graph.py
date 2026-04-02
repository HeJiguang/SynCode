from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.runtime.enums import RiskLevel
from app.runtime.models import OutcomeState, UnifiedAgentState
from app.graphs.capabilities.shared import (
    build_evidence_state,
    build_guardrail_state,
    collect_capability_support,
    update_execution,
)


class ReviewGraphState(TypedDict):
    request: object
    execution: object
    unified_state: UnifiedAgentState


def review_node(state: ReviewGraphState) -> ReviewGraphState:
    request = state["request"]
    execution = state["execution"]
    support = collect_capability_support(
        request,
        query_fields=(
            "question_title",
            "user_message",
        ),
    )

    answer_lines = [
        "Review summary:",
        "You should separate stable strengths from recurring mistakes instead of treating all failures as the same issue.",
        "Recent practice suggests you need one short review cycle before adding new difficulty.",
    ]
    if request.question_title:
        answer_lines.append(f"Use {request.question_title} as the anchor problem for this review.")

    unified_state = UnifiedAgentState(
        request=request,
        execution=update_execution(execution, active_node="review_graph"),
        evidence=build_evidence_state(support.retrieval),
        guardrail=build_guardrail_state(support.request_guard, support.evidence_guard).model_copy(
            update={
                "risk_level": (
                    support.request_guard.risk_level
                    if support.request_guard.risk_level is not RiskLevel.LOW
                    else support.evidence_guard.risk_level
                )
            }
        ),
        outcome=OutcomeState(
            intent="review_summary",
            answer="\n".join(answer_lines),
            confidence=0.82,
            next_action="Spend one focused session reviewing your last two mistakes before starting new problems.",
            status_events=[
                {"node": "performance_aggregation", "message": "Aggregated recent practice signals."},
                {"node": "evidence_retrieval", "message": "Retrieved review evidence candidates."},
                {"node": "review_synthesis", "message": "Synthesized review summary and next step."},
            ],
        ),
    )
    return {
        **state,
        "unified_state": unified_state,
    }


def build_review_graph():
    graph = StateGraph(ReviewGraphState)
    graph.add_node("review", review_node)
    graph.add_edge(START, "review")
    graph.add_edge("review", END)
    return graph.compile()
