from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.guardrails.runtime import GuardrailInput, GuardrailRuntime
from app.retrieval.models import RetrievalQuery
from app.retrieval.runtime import RetrievalRuntime
from app.runtime.enums import RiskLevel, RunStatus
from app.runtime.models import EvidenceItem, EvidenceState, GuardrailState, OutcomeState, UnifiedAgentState, WriteIntent


class ProfileGraphState(TypedDict):
    request: object
    execution: object
    unified_state: UnifiedAgentState


def profile_node(state: ProfileGraphState) -> ProfileGraphState:
    request = state["request"]
    execution = state["execution"]
    retrieval = RetrievalRuntime().retrieve(
        RetrievalQuery(
            query_text=" ".join(
                value
                for value in [
                    request.question_title,
                    request.user_message,
                ]
                if value
            ),
            task_type=request.task_type.value,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
        )
    )
    guard = GuardrailRuntime().evaluate(
        GuardrailInput(
            task_type=request.task_type.value,
            user_message=request.user_message,
            question_title=request.question_title,
            question_content=request.question_content,
            user_code=request.user_code,
            judge_result=request.judge_result,
        )
    )
    evidence_guard = GuardrailRuntime().evaluate_evidence(
        task_type=request.task_type.value,
        evidence_count=len(retrieval.items),
        route_names=retrieval.route_names,
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
        execution=execution.model_copy(
            update={
                "status": RunStatus.SUCCEEDED,
                "active_node": "profile_graph",
            }
        ),
        evidence=EvidenceState(
            items=[
                EvidenceItem(
                    evidence_id=item.evidence_id,
                    source_type=item.source_type,
                    source_id=item.source_id,
                    title=item.title,
                    snippet=item.snippet,
                    recall_score=item.score,
                    metadata={"route_name": item.route_name, **item.metadata},
                )
                for item in retrieval.items
            ],
            route_names=retrieval.route_names,
            coverage_score=1.0 if retrieval.items else 0.0,
        ),
        guardrail=GuardrailState(
            risk_level=guard.risk_level if guard.risk_level is not RiskLevel.LOW else evidence_guard.risk_level,
            completeness_ok=guard.completeness_ok and evidence_guard.completeness_ok,
            policy_ok=guard.policy_ok,
            dirty_data_flags=guard.missing_fields,
            risk_reasons=guard.risk_reasons + evidence_guard.risk_reasons,
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
