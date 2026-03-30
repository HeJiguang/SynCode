from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from app.graph.edges import ANALYZE_FAILURE, RECOMMEND_QUESTION
from app.graph.builder import build_graph
from app.graphs.capabilities.diagnose_graph import build_diagnose_graph
from app.graphs.capabilities.recommend_graph import build_recommend_graph
from app.guardrails.runtime import GuardrailInput, GuardrailRuntime
from app.retrieval.runtime import RetrievalRuntime
from app.retrieval.models import RetrievalQuery
from app.runtime.enums import RiskLevel, RunStatus, TaskType
from app.runtime.models import EvidenceItem, EvidenceState, GuardrailState, UnifiedAgentState
from app.services import chat_assistant


class TutorGraphState(TypedDict):
    request: object
    execution: object
    stream_mode: NotRequired[bool]
    unified_state: UnifiedAgentState


def _safe_evidence_guard(
    guardrail_runtime,
    *,
    task_type: str,
    evidence_count: int,
    route_names: list[str] | None = None,
):
    if not hasattr(guardrail_runtime, "evaluate_evidence"):
        from app.guardrails.runtime import GuardrailOutput  # noqa: WPS433

        return GuardrailOutput(
            risk_level=RiskLevel.LOW,
            completeness_ok=True,
            policy_ok=True,
        )
    try:
        return guardrail_runtime.evaluate_evidence(
            task_type=task_type,
            evidence_count=evidence_count,
            route_names=route_names,
        )
    except TypeError:
        return guardrail_runtime.evaluate_evidence(
            task_type=task_type,
            evidence_count=evidence_count,
        )


def _higher_risk(left: RiskLevel, right: RiskLevel) -> RiskLevel:
    order = {
        RiskLevel.LOW: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.HIGH: 3,
    }
    return left if order[left] >= order[right] else right


def _hydrate_request_from_legacy_result(request, result: dict):
    return request.model_copy(
        update={
            "conversation_id": result.get("conversation_id") or request.conversation_id,
            "question_id": result.get("question_id") or request.question_id,
            "question_title": result.get("question_title") or request.question_title,
            "question_content": result.get("question_content") or request.question_content,
            "user_code": result.get("user_code") or request.user_code,
            "judge_result": result.get("judge_result") or request.judge_result,
            "user_message": result.get("user_message") or request.user_message,
        }
    )


def _merge_status_events(result: dict, delegated_state: UnifiedAgentState):
    merged = [
        {"node": "retrieval_runtime", "message": "Built retrieval evidence set."},
        {"node": "guardrail_runtime", "message": "Evaluated request and output guardrails."},
    ]
    merged.extend(
        {"node": str(item["node"]), "message": str(item["message"])}
        for item in result.get("status_events") or []
    )
    merged.extend(delegated_state.outcome.status_events)
    return delegated_state.outcome.model_copy(update={"status_events": merged})


def _delegate_intent(
    request,
    execution,
    result: dict,
) -> UnifiedAgentState | None:
    hydrated_request = _hydrate_request_from_legacy_result(request, result)
    intent = str(result.get("intent") or "")
    if intent == ANALYZE_FAILURE:
        payload = {
            "request": hydrated_request.model_copy(update={"task_type": TaskType.DIAGNOSIS}),
            "execution": execution,
        }
        delegated = build_diagnose_graph().invoke(payload)["unified_state"]
        return delegated.model_copy(update={"outcome": _merge_status_events(result, delegated)})
    if intent == RECOMMEND_QUESTION:
        payload = {
            "request": hydrated_request.model_copy(update={"task_type": TaskType.RECOMMENDATION}),
            "execution": execution,
        }
        delegated = build_recommend_graph().invoke(payload)["unified_state"]
        return delegated.model_copy(update={"outcome": _merge_status_events(result, delegated)})
    return None


def tutor_node(state: TutorGraphState) -> TutorGraphState:
    request = state["request"]
    execution = state["execution"]
    stream_mode = bool(state.get("stream_mode"))

    retrieval_runtime = RetrievalRuntime()
    retrieval_result = retrieval_runtime.retrieve(
        RetrievalQuery(
            query_text=" ".join(
                value
                for value in [
                    request.question_title,
                    request.question_content,
                    request.judge_result,
                    request.user_message,
                ]
                if value
            ),
            task_type=request.task_type.value,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
        )
    )

    guardrail_runtime = GuardrailRuntime()
    input_guard = guardrail_runtime.evaluate(
        GuardrailInput(
            task_type=request.task_type.value,
            user_message=request.user_message,
            question_title=request.question_title,
            question_content=request.question_content,
            user_code=request.user_code,
            judge_result=request.judge_result,
        )
    )
    evidence_guard = _safe_evidence_guard(
        guardrail_runtime,
        task_type=request.task_type.value,
        evidence_count=len(retrieval_result.items),
        route_names=retrieval_result.route_names,
    )

    result = build_graph().invoke(
        {
            "trace_id": request.trace_id,
            "user_id": request.user_id,
            "conversation_id": request.conversation_id,
            "question_id": request.question_id,
            "question_title": request.question_title,
            "question_content": request.question_content,
            "user_code": request.user_code,
            "judge_result": request.judge_result,
            "user_message": request.user_message,
        }
    )
    if not stream_mode:
        delegated_state = _delegate_intent(request, execution, result)
        if delegated_state is not None:
            return {
                **state,
                "unified_state": delegated_state,
            }

    answer = str(result.get("final_answer") or "I need more context before I can help precisely.")
    confidence = float(result.get("confidence") or 0.2)
    next_action = str(result.get("next_action") or "Send one more concrete failing example.")
    model_name = None
    output_guard = None

    if not stream_mode:
        answer, confidence, next_action, model_name = chat_assistant.generate_chat_answer(result)
        output_guard = guardrail_runtime.evaluate_output(
            answer=answer,
            evidence_count=len(retrieval_result.items),
        )

    combined_risk = input_guard.risk_level
    combined_risk = _higher_risk(combined_risk, evidence_guard.risk_level)
    if output_guard is not None:
        combined_risk = _higher_risk(input_guard.risk_level, output_guard.risk_level)
        combined_risk = _higher_risk(combined_risk, evidence_guard.risk_level)

    execution = execution.model_copy(
        update={
            "status": RunStatus.SUCCEEDED,
            "active_node": "tutor_graph",
            "model_name": model_name,
        }
    )

    unified_state = UnifiedAgentState(
        request=request,
        execution=execution,
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
                for item in retrieval_result.items
            ],
            route_names=retrieval_result.route_names,
            coverage_score=1.0 if retrieval_result.items else 0.0,
        ),
        guardrail=GuardrailState(
            risk_level=combined_risk,
            completeness_ok=input_guard.completeness_ok and evidence_guard.completeness_ok,
            policy_ok=(
                input_guard.policy_ok
                and evidence_guard.policy_ok
                and (output_guard.policy_ok if output_guard is not None else True)
            ),
            dirty_data_flags=input_guard.missing_fields + evidence_guard.missing_fields,
            risk_reasons=(
                input_guard.risk_reasons
                + evidence_guard.risk_reasons
                + (output_guard.risk_reasons if output_guard is not None else [])
            ),
        ),
        outcome=chat_assistant_safe_outcome(
            result,
            answer,
            confidence,
            next_action,
            response_payload={
                "assistant_state": result,
                "stream_mode": stream_mode,
            },
        ),
    )
    return {
        **state,
        "unified_state": unified_state,
    }


def chat_assistant_safe_outcome(
    result: dict,
    answer: str,
    confidence: float,
    next_action: str,
    *,
    response_payload: dict | None = None,
):
    from app.runtime.models import OutcomeState

    status_events = [
        {"node": "retrieval_runtime", "message": "Built retrieval evidence set."},
        {"node": "guardrail_runtime", "message": "Evaluated request and output guardrails."},
    ]
    status_events.extend(
        {"node": str(item["node"]), "message": str(item["message"])}
        for item in result.get("status_events") or []
    )
    return OutcomeState(
        intent=str(result.get("intent") or "ask_for_context"),
        answer=answer,
        next_action=next_action,
        confidence=confidence,
        status_events=status_events,
        response_payload=response_payload or {},
    )


def build_tutor_graph():
    graph = StateGraph(TutorGraphState)
    graph.add_node("tutor", tutor_node)
    graph.add_edge(START, "tutor")
    graph.add_edge("tutor", END)
    return graph.compile()
