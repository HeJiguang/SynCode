from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.guardrails.runtime import GuardrailInput, GuardrailRuntime
from app.retrieval.models import RetrievalQuery
from app.retrieval.runtime import RetrievalRuntime
from app.runtime.enums import RiskLevel, RunStatus
from app.runtime.models import EvidenceItem, EvidenceState, GuardrailState, OutcomeState, UnifiedAgentState


class DiagnoseGraphState(TypedDict):
    request: object
    execution: object
    unified_state: UnifiedAgentState


def diagnose_node(state: DiagnoseGraphState) -> DiagnoseGraphState:
    request = state["request"]
    execution = state["execution"]
    retrieval = RetrievalRuntime().retrieve(
        RetrievalQuery(
            query_text=" ".join(
                value
                for value in [
                    request.question_title,
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

    judge_signal = (request.judge_result or "unknown").upper()
    if "TLE" in judge_signal:
        diagnosis = "The most likely issue is time complexity or a non-terminating loop."
        next_action = "Count the worst-case operations and test the largest allowed input."
    elif "RE" in judge_signal:
        diagnosis = "The most likely issue is an exception path such as index, null, or parsing failure."
        next_action = "Re-run the smallest crashing input and inspect every array and parser boundary."
    elif "CE" in judge_signal:
        diagnosis = "The most likely issue is a compile-time mismatch in syntax, imports, or method signatures."
        next_action = "Fix the first compiler error before changing algorithm logic."
    else:
        diagnosis = "The most likely issue is a wrong answer caused by a missed edge case or incorrect state update."
        next_action = "Trace the smallest failing input by hand and compare every intermediate value."

    answer_lines = [
        f"Diagnosis summary: {diagnosis}",
        f"Judge signal: {request.judge_result or 'not provided'}",
    ]
    if request.question_title:
        answer_lines.append(f"Question: {request.question_title}")
    answer_lines.append(f"Suggested next step: {next_action}")

    unified_state = UnifiedAgentState(
        request=request,
        execution=execution.model_copy(
            update={
                "status": RunStatus.SUCCEEDED,
                "active_node": "diagnose_graph",
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
            intent="analyze_failure",
            answer="\n".join(answer_lines),
            confidence=0.9 if request.judge_result else 0.72,
            next_action=next_action,
            status_events=[
                {"node": "signal_analysis", "message": "Derived judge signal for diagnosis."},
                {"node": "evidence_retrieval", "message": "Retrieved diagnosis evidence candidates."},
                {"node": "hypothesis_generation", "message": "Generated primary diagnosis hypothesis."},
            ],
        ),
    )
    return {
        **state,
        "unified_state": unified_state,
    }


def build_diagnose_graph():
    graph = StateGraph(DiagnoseGraphState)
    graph.add_node("diagnose", diagnose_node)
    graph.add_edge(START, "diagnose")
    graph.add_edge("diagnose", END)
    return graph.compile()
