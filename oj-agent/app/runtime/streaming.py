from collections.abc import Iterator, Mapping

# 导入安全护栏、运行时引擎、状态枚举和数据模型
from app.guardrails.runtime import GuardrailRuntime
from app.runtime.engine import prepare_chat_stream_state, record_chat_state
from app.runtime.enums import RiskLevel
from app.runtime.models import UnifiedAgentState
# 导入请求格式和流式输出的各种事件模型（元数据、过程状态、增量数据、最终结果、错误）
from app.schemas.chat_request import ChatRequest
from app.schemas.stream_events import DeltaEvent, ErrorEvent, FinalEvent, MetaEvent, StatusEvent
# 导入底层大模型服务工具和 SSE (Server-Sent Events) 事件打包工具
from app.services import chat_assistant
from app.services.stream_emitter import to_sse_event


def _higher_risk(left: RiskLevel, right: RiskLevel) -> RiskLevel:
    # 【辅助函数】比较两个风险等级，返回风险更高的那个（风控的“就高原则”）
    
    # 定义风险等级的权重字典，数值越大风险越高
    order = {
        RiskLevel.LOW: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.HIGH: 3,
    }
    # 如果左边的分数 >= 右边的分数，返回左边的风险等级，否则返回右边
    return left if order[left] >= order[right] else right


def _assistant_state(state: UnifiedAgentState) -> dict:
    # 【辅助函数】从庞大的全局状态 (UnifiedAgentState) 中，
    # 单独把大模型需要的 "assistant_state"（助手上下文，通常包含历史对话等）提取出来变成字典
    return dict(state.outcome.response_payload.get("assistant_state") or {})


def _finalize_state(
    state: UnifiedAgentState,
    *,
    answer: str,
    confidence: float,
    next_action: str,
    model_name: str | None,
) -> UnifiedAgentState:
    # 【核心质检函数】对话结束时，将最终生成的答案和评估结果更新到原来的状态大包中
    
    # 1. 触发输出安全护栏检查（比如检查 AI 生成的回答里有没有违规内容）
    output_guard = GuardrailRuntime().evaluate_output(
        answer=answer,
        evidence_count=len(state.evidence.items),
    )
    
    # 2. Pydantic 的 model_copy 功能：它不会修改原数据，而是复印一份并只替换（update）里面指定的内容。
    # 更新安全护栏状态：合并原有的风险和最新输出评估的风险
    guardrail = state.guardrail.model_copy(
        update={
            "risk_level": _higher_risk(state.guardrail.risk_level, output_guard.risk_level),
            "policy_ok": state.guardrail.policy_ok and output_guard.policy_ok,
            "risk_reasons": state.guardrail.risk_reasons + output_guard.risk_reasons,
        }
    )
    
    # 更新执行状态：记录真正用来生成答案的模型名称
    execution = state.execution.model_copy(
        update={
            "model_name": model_name or state.execution.model_name,
        }
    )
    
    # 更新输出状态：填入最终的回答、置信度以及下一步建议动作
    outcome = state.outcome.model_copy(
        update={
            "answer": answer,
            "confidence": confidence,
            "next_action": next_action,
        }
    )
    
    # 3. 把上面更新好的这三个小包，重新塞回一个新的 UnifiedAgentState 大包里并返回
    return state.model_copy(
        update={
            "execution": execution,
            "guardrail": guardrail,
            "outcome": outcome,
        }
    )


def stream_chat_request(
    request: ChatRequest,
    headers: Mapping[str, str | None],
) -> Iterator[str]:
    # 【主函数】处理流式聊天请求。返回值 Iterator[str] 代表这是一个会多次通过 yield 返回字符串的迭代器/生成器
    
    # 1. 初始化：让底层引擎准备好上下文图状态，并提取出 assistant_state
    state = prepare_chat_stream_state(request, headers)
    assistant_state = _assistant_state(state)

    # 2. 发送见面礼（Meta 事件）：通过 yield 吐出第一条系统级消息，告诉前端请求已收到，准备开始处理
    yield to_sse_event(
        "meta",
        MetaEvent(
            trace_id=state.request.trace_id,
            graph_version="phase-1-runtime",
            mode="llm",
        ),
    )

    # 3. 发送过程状态（Status 事件）：循环遍历之前引擎执行经过的节点（如搜索中、总结中），推给前端展示进度
    for status in state.outcome.status_events:
        yield to_sse_event(
            "status",
            StatusEvent(
                node=str(status.get("node") or "unknown"),
                message=str(status.get("message") or ""),
            ),
        )

    # 4. 快车道拦截：如果在调用大模型前就已经有答案了（比如触发了规则拦截或缓存命中）
    if not assistant_state and state.outcome.answer:
        # 直接进行数据结算
        final_state = _finalize_state(
            state,
            answer=state.outcome.answer,
            confidence=state.outcome.confidence or 0.0,
            next_action=state.outcome.next_action
            or "Send the question statement, your code, and the latest judge result.",
            model_name=state.execution.model_name,
        )
        # 记录到数据库
        record_chat_state(final_state)
        # 发送 Final 事件告诉前端结束了
        yield to_sse_event(
            "final",
            FinalEvent(
                answer=final_state.outcome.answer or "",
                confidence=final_state.outcome.confidence or 0.0,
                next_action=final_state.outcome.next_action
                or "Send the question statement, your code, and the latest judge result.",
            ),
        )
        # 提前结束整个函数
        return

    # 5. 常规大模型生成流程：初始化变量
    answer = ""
    model_name = state.execution.model_name
    streaming_error: str | None = None
    
    # 尝试流式获取大模型输出（打字机效果核心逻辑）
    try:
        # stream_chat_answer 会一段一段（chunk）地吐出生成的文字
        for chunk in chat_assistant.stream_chat_answer(assistant_state):
            answer += chunk  # 把碎文字拼接到完整答案里
            # 发送 Delta（增量）事件给前端，前端收到后追加显示文字
            yield to_sse_event("delta", DeltaEvent(answer=answer))
    except Exception as exc:  # pragma: no cover - defensive runtime fallback
        # 如果流式传输网络断了或报错，记录错误信息，准备进行兜底
        streaming_error = str(exc)

    # 6. 处理生成结果或兜底
    if answer:
        # 如果流式生成成功，提取置信度和建议动作，并将结果记录到短期记忆中
        confidence = float(assistant_state.get("confidence") or state.outcome.confidence or 0.2)
        next_action = str(
            assistant_state.get("next_action")
            or state.outcome.next_action
            or "Send one more concrete failing example."
        )
        chat_assistant.remember_generated_answer(assistant_state, answer, confidence, next_action)
        model_name = model_name or "streaming-runtime"
    else:
        # 兜底逻辑：如果刚才由于某些异常一个字都没流式输出出来，尝试同步一次性生成整个回答
        answer, confidence, next_action, model_name = chat_assistant.generate_chat_answer(assistant_state)
        # 把刚才的流式报错信息作为 Error 事件发送给前端排查
        if streaming_error:
            yield to_sse_event("error", ErrorEvent(message=streaming_error))

    # 7. 收尾：执行结算质检，将包含完整答案的状态落库保存
    final_state = _finalize_state(
        state,
        answer=answer,
        confidence=confidence,
        next_action=next_action,
        model_name=model_name,
    )
    record_chat_state(final_state)

    # 8. 最后一步：发送 Final 事件，通知前端大模型回答彻底完毕，可以停止打字机特效了
    yield to_sse_event(
        "final",
        FinalEvent(
            answer=answer,
            confidence=confidence,
            next_action=next_action,
        ),
    )