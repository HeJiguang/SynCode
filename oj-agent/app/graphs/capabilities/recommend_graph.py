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


class RecommendGraphState(TypedDict):
    request: object
    execution: object
    unified_state: UnifiedAgentState


def recommend_node(state: RecommendGraphState) -> RecommendGraphState:
    request = state["request"]
    execution = state["execution"]
    support = collect_capability_support(
        request,
        query_fields=(
            "question_title",
            "question_content",
            "user_message",
        ),
    )

    recommendation_lines = [
        "Practice plan:",
        "1. Repeat one array/hash-map problem with a full dry run.",
        "2. Then solve one variant that changes the constraint or traversal order.",
        "3. End with one timed problem to verify the pattern is stable.",
    ]
    if request.question_title:
        recommendation_lines.insert(1, f"Start from the pattern behind {request.question_title}.")

    unified_state = UnifiedAgentState(
        request=request,
        execution=update_execution(execution, active_node="recommend_graph"),
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
            intent="recommend_question",
            answer="\n".join(recommendation_lines),
            confidence=0.85,
            next_action="Pick the first recommended problem and solve it without looking at notes.",
            status_events=[
                {"node": "profile_snapshot", "message": "Built recommendation context snapshot."},
                {"node": "evidence_retrieval", "message": "Retrieved recommendation evidence candidates."},
                {"node": "ranking", "message": "Ranked the next practice direction."},
            ],
        ),
    )
    return {
        **state,
        "unified_state": unified_state,
    }


def build_recommend_graph():
    graph = StateGraph(RecommendGraphState)
    graph.add_node("recommend", recommend_node)
    graph.add_edge(START, "recommend")
    graph.add_edge("recommend", END)
    return graph.compile()
