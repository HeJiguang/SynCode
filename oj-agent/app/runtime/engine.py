from collections.abc import Mapping
from typing import Callable

from app.evaluation.hooks import build_chat_eval_record, build_plan_eval_record
from app.evaluation.store import evaluation_store
from app.observability.query_ledger import QueryLedgerEntry, query_ledger
from app.observability.trace import NodeTraceEvent, RunTrace, trace_store
from app.services.llm_runtime_service import execute_chat_with_llm, execute_training_plan_with_llm
from app.runtime.models import RequestContext, UnifiedAgentState
from app.schemas.training_plan_request import TrainingPlanRequest


def invoke_request_context(request_context: RequestContext) -> UnifiedAgentState:
    """Run one request through the LLM-only runtime."""
    return execute_chat_with_llm(request_context)


def _record_runtime_state(
    state: UnifiedAgentState,
    *,
    output_type: str,
    eval_builder: Callable[[UnifiedAgentState], dict],
) -> None:
    trace_store.record_run(
        RunTrace(
            trace_id=state.request.trace_id,
            run_id=state.execution.run_id,
            graph_name=state.execution.graph_name,
            task_type=state.request.task_type.value,
            user_id=state.request.user_id,
        )
    )

    recorded_nodes: list[str] = []
    for status_event in state.outcome.status_events:
        node_name = str(status_event.get("node") or "unknown")
        if node_name in recorded_nodes:
            continue
        trace_store.record_node_event(
            NodeTraceEvent(
                trace_id=state.request.trace_id,
                run_id=state.execution.run_id,
                graph_name=state.execution.graph_name,
                node_name=node_name,
                status=state.execution.status.value,
            )
        )
        recorded_nodes.append(node_name)

    active_node = state.execution.active_node or "unknown"
    if active_node not in recorded_nodes:
        trace_store.record_node_event(
            NodeTraceEvent(
                trace_id=state.request.trace_id,
                run_id=state.execution.run_id,
                graph_name=state.execution.graph_name,
                node_name=active_node,
                status=state.execution.status.value,
            )
        )
        recorded_nodes.append(active_node)

    query_ledger.append(
        QueryLedgerEntry(
            trace_id=state.request.trace_id,
            run_id=state.execution.run_id,
            user_id=state.request.user_id,
            task_type=state.request.task_type.value,
            request_text=state.request.user_message,
            graph_path=[state.execution.graph_name, *recorded_nodes],
            route_names=list(state.evidence.route_names),
            evidence_sources=[item.source_id for item in state.evidence.items],
            output_type=output_type,
            risk_level=state.guardrail.risk_level.value,
            token_cost=0,
            latency_ms=0,
        )
    )
    evaluation_store.append(eval_builder(state))


def record_chat_state(state: UnifiedAgentState) -> None:
    _record_runtime_state(
        state,
        output_type=state.outcome.intent or "llm_chat",
        eval_builder=build_chat_eval_record,
    )


def record_training_plan_state(state: UnifiedAgentState) -> None:
    _record_runtime_state(
        state,
        output_type=state.outcome.intent or "training_plan",
        eval_builder=build_plan_eval_record,
    )


def execute_request_context(
    request_context: RequestContext,
    headers: Mapping[str, str | None],
) -> UnifiedAgentState:
    del headers
    state = invoke_request_context(request_context)
    record_chat_state(state)
    return state


def execute_training_plan_request(request: TrainingPlanRequest) -> UnifiedAgentState:
    state = execute_training_plan_with_llm(request)
    record_training_plan_state(state)
    return state
