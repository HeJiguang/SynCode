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


class DiagnoseGraphState(TypedDict):
    request: object
    execution: object
    unified_state: UnifiedAgentState


def diagnose_node(state: DiagnoseGraphState) -> DiagnoseGraphState:
    request = state["request"]
    execution = state["execution"]
    support = collect_capability_support(
        request,
        query_fields=(
            "question_title",
            "judge_result",
            "user_message",
        ),
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
        execution=update_execution(execution, active_node="diagnose_graph"),
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
