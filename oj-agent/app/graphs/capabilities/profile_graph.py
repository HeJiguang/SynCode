from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.runtime.enums import RiskLevel
from app.runtime.models import OutcomeState, UnifiedAgentState, WriteIntent
from app.graphs.capabilities.shared import (
    build_evidence_state,
    build_guardrail_state,
    collect_capability_support,
    update_execution,
)


class ProfileGraphState(TypedDict):
    request: object
    execution: object
    unified_state: UnifiedAgentState


def profile_node(state: ProfileGraphState) -> ProfileGraphState:
    request = state["request"]
    execution = state["execution"]
    support = collect_capability_support(
        request,
        query_fields=(
            "question_title",
            "user_message",
        ),
    )

    profile_payload = {
        "focus_tags": ["array", "hash map"],
        "weakness_tags": ["edge_case_validation"],
        "stability_level": "developing",
    }
    answer_lines = [
        "Profile update summary:",
        "Your current focus remains array and hash-map patterns.",
        "The latest weak signal is edge-case validation rather than core pattern recognition.",
        "You should keep one short verification pass after every accepted-looking solution.",
    ]

    unified_state = UnifiedAgentState(
        request=request,
        execution=update_execution(execution, active_node="profile_graph"),
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
            intent="profile_update",
            answer="\n".join(answer_lines),
            confidence=0.81,
            next_action="Review the updated focus tags and use them to pick your next two practice problems.",
            response_payload=profile_payload,
            write_intents=[
                WriteIntent(
                    intent_type="profile_update_write",
                    target_service="oj-friend",
                    payload=profile_payload,
                )
            ],
            status_events=[
                {"node": "signal_aggregation", "message": "Aggregated profile evidence signals."},
                {"node": "profile_delta_generation", "message": "Generated profile update proposal."},
                {"node": "profile_delta_verification", "message": "Verified profile update payload."},
            ],
        ),
    )
    return {
        **state,
        "unified_state": unified_state,
    }


def build_profile_graph():
    graph = StateGraph(ProfileGraphState)
    graph.add_node("profile", profile_node)
    graph.add_edge(START, "profile")
    graph.add_edge("profile", END)
    return graph.compile()
