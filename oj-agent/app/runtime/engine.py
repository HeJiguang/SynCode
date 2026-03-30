from collections.abc import Mapping
from typing import Callable

from app.core.config import load_settings
from app.core.identity import normalize_chat_request
from app.evaluation.hooks import build_chat_eval_record, build_plan_eval_record
from app.evaluation.store import evaluation_store
from app.observability.query_ledger import QueryLedgerEntry, query_ledger
from app.observability.trace import NodeTraceEvent, RunTrace, trace_store
from app.graphs.supervisor_graph import build_supervisor_graph
from app.runtime.context import build_request_context
from app.runtime.enums import TaskType
from app.runtime.models import RequestContext, UnifiedAgentState
from app.schemas.chat_request import ChatRequest
from app.schemas.training_plan_request import TrainingPlanRequest


# 将用户的request请求打包成RequestContext
def build_chat_request_context(
    request: ChatRequest,
    headers: Mapping[str, str | None],
) -> RequestContext:
    """
    构建聊天请求的上下文数据结构。
    首先从传入的 raw headers（HTTP 请求头）中解析并标准化用户信息（如果在网关层被注入），
    然后将其转换为供大模型图计算引擎统一使用的 RequestContext 核心内部结构。
    """
    normalized_request = normalize_chat_request(
        request,
        headers,
        load_settings().gateway_user_id_header,
    )
    return build_request_context(
        trace_id=normalized_request.trace_id or "unknown-trace",
        user_id=normalized_request.user_id or "unknown-user",
        task_type=TaskType.CHAT,
        user_message=normalized_request.user_message,
        conversation_id=normalized_request.conversation_id,
        question_id=normalized_request.question_id,
        question_title=normalized_request.question_title,
        question_content=normalized_request.question_content,
        user_code=normalized_request.user_code,
        judge_result=normalized_request.judge_result,
    )


def invoke_chat_runtime(
    request_context: RequestContext,
    *,
    stream_mode: bool = False,
) -> UnifiedAgentState:
    """
    触发并执行大模型聊天运行时。
    动态构建顶层的 Supervisor Graph（主管路由图），接着向里喂入构造好的上下文，并执行完整的业务流。
    如果配置了 stream_mode=True 则在图内部走流式分支。
    返回图执行完毕后最终产出的聚合状态 UnifiedAgentState。
    """
    graph = build_supervisor_graph()
    payload = {"request": request_context}
    if stream_mode:
        payload["stream_mode"] = True
    result = graph.invoke(payload)
    return result["unified_state"]


def _record_runtime_state(
    state: UnifiedAgentState,
    *,
    output_type: str,
    eval_builder: Callable[[UnifiedAgentState], dict],
) -> None:
    """
    私有辅助函数：持久化存储整个大模型执行生命周期中的可观测性数据。
    主要做三件事：
    1. 记录运行轨迹 (trace_store)：包含 Run 本身和图流转途径中所有 Node 的状态日志。
    2. 记录查询账本 (query_ledger)：对每一次大模型的检索消耗、Token、风险审查结果登记造册，用于运营侧看数据。
    3. 评测数据入库 (evaluation_store)：结合传入的 eval_builder，把用户的提问和 AI 的回答打造成标准语料库格式。
    """
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

    # 汇总这笔请求流经的所有节点路径
    graph_path = [state.execution.graph_name, *recorded_nodes]
    query_ledger.append(
        QueryLedgerEntry(
            trace_id=state.request.trace_id,
            run_id=state.execution.run_id,
            user_id=state.request.user_id,
            task_type=state.request.task_type.value,
            request_text=state.request.user_message,
            graph_path=graph_path,
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
    """记录「聊天请求」类型的可观测性日志及评测数据。"""
    _record_runtime_state(
        state,
        output_type=state.outcome.intent or "chat_response",
        eval_builder=build_chat_eval_record,
    )


def record_training_plan_state(state: UnifiedAgentState) -> None:
    """记录「训练路径规划请求」类型的可观测性日志及评测数据。"""
    _record_runtime_state(
        state,
        output_type=state.outcome.intent or "training_plan",
        eval_builder=build_plan_eval_record,
    )


def prepare_chat_stream_state(
    request: ChatRequest,
    headers: Mapping[str, str | None],
) -> UnifiedAgentState:
    """
    为「流式聊天请求」初始化并执行运行时。
    流式请求特殊在于，SSE 推送结束前可能不会记录结果，这里负责启动流式处理的执行。
    """
    request_context = build_chat_request_context(request, headers)
    return invoke_chat_runtime(request_context, stream_mode=True)


def execute_chat_request(
    request: ChatRequest,
    headers: Mapping[str, str | None],
) -> UnifiedAgentState:
    """
    为「阻塞式/同步聊天请求」执行核心逻辑。
    1. 构建运行上下文；
    2. 唤起 Agent 大模型逻辑图执行；
    3. 同步执行完毕后，调用记录埋点入库。
    """
    request_context = build_chat_request_context(request, headers)
    state = invoke_chat_runtime(request_context)
    record_chat_state(state)
    return state


def execute_training_plan_request(request: TrainingPlanRequest) -> UnifiedAgentState:
    """
    为「训练路径规划」请求执行核心业务流。
    此接口不需要经过复杂的聊天解析步骤，直接构造内部请求环境喂入 Supervisor 节点，
    执行完毕后同样进行异步日志记录。
    """
    request_context = build_request_context(
        trace_id=request.trace_id,
        user_id=str(request.user_id),
        task_type=TaskType.TRAINING_PLAN,
        user_message="Generate training plan.",
    )
    graph = build_supervisor_graph()
    result = graph.invoke(
        {
            "request": request_context,
            "training_request": request,
        }
    )
    state = result["unified_state"]
    record_training_plan_state(state)
    return state
