from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.guardrails.runtime import GuardrailInput, GuardrailRuntime
from app.retrieval.models import RetrievalQuery
from app.retrieval.runtime import RetrievalRuntime
from app.runtime.enums import RiskLevel, RunStatus
from app.runtime.models import EvidenceItem, EvidenceState, GuardrailState, OutcomeState, UnifiedAgentState


class RecommendGraphState(TypedDict):
    request: object
    execution: object
    unified_state: UnifiedAgentState


def recommend_node(state: RecommendGraphState) -> RecommendGraphState:
    request = state["request"]
    execution = state["execution"]
    retrieval = RetrievalRuntime().retrieve(
        RetrievalQuery(
            query_text=" ".join(
                value
                for value in [
                    request.question_title,
                    request.question_content,
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
        execution=execution.model_copy(
            update={
                "status": RunStatus.SUCCEEDED,
                "active_node": "recommend_graph",
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
