from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.guardrails.runtime import GuardrailInput, GuardrailRuntime
from app.retrieval.models import RetrievalQuery
from app.retrieval.runtime import RetrievalRuntime
from app.runtime.enums import RiskLevel, RunStatus
from app.runtime.models import EvidenceItem, EvidenceState, GuardrailState, OutcomeState, UnifiedAgentState


class ReviewGraphState(TypedDict):
    request: object
    execution: object
    unified_state: UnifiedAgentState


def review_node(state: ReviewGraphState) -> ReviewGraphState:
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

    answer_lines = [
        "Review summary:",
        "You should separate stable strengths from recurring mistakes instead of treating all failures as the same issue.",
        "Recent practice suggests you need one short review cycle before adding new difficulty.",
    ]
    if request.question_title:
        answer_lines.append(f"Use {request.question_title} as the anchor problem for this review.")

    unified_state = UnifiedAgentState(
        request=request,
        execution=execution.model_copy(
            update={
                "status": RunStatus.SUCCEEDED,
                "active_node": "review_graph",
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
