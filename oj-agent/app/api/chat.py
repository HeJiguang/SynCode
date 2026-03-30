from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.runtime.engine import execute_chat_request
from app.runtime.streaming import stream_chat_request
from app.schemas.chat_request import ChatRequest
from app.schemas.chat_response import ChatResponse


# 定义聊天模块的路由，所有接口路径前缀为 /api/chat，并在 API 文档中归类为 "chat"
router = APIRouter(prefix="/api/chat", tags=["chat"])


def _to_chat_response(state) -> ChatResponse:
    """
    辅助函数：将 AI 引擎执行后的内部状态对象 (state) 转换为统一标准格式的返回对象 (ChatResponse)。
    如果内部状态中某些字段为空，则提供默认的占位符/提示信息。
    """
    return ChatResponse(
        trace_id=state.request.trace_id,
        intent=state.outcome.intent or "ask_for_context",
        answer=state.outcome.answer or "I need more context before I can help precisely.",
        confidence=state.outcome.confidence or 0.0,
        next_action=state.outcome.next_action or "Send the question statement, current code, and latest judge result.",
    )


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, raw_request: Request) -> ChatResponse:
    """
    基础聊天接口（阻塞式）：接收用户的聊天请求，调用引擎进行处理，并以 JSON 格式一次性返回完整结果。
    同时传递 raw_request.headers 给后端引擎，以便携带 trace_id 或认证信息。
    """
    state = execute_chat_request(request, raw_request.headers)
    return _to_chat_response(state)


@router.post("/detail", response_model=ChatResponse)
def chat_detail(request: ChatRequest, raw_request: Request) -> ChatResponse:
    """
    详情聊天接口：功能与基础聊天接口完全一致，内部也是调用它。
    通常用于前端在不同业务页面或场景下使用，这有助于后端的接口统计或权限区分。
    """
    return chat(request, raw_request)


@router.post("/stream")
def chat_stream(request: ChatRequest, raw_request: Request) -> StreamingResponse:
    """
    流式聊天接口：使用 Server-Sent Events (SSE) 技术。
    该接口不会阻塞等待大模型全部生成完毕，而是将 AI 生成的回复内容像“打字机”一样逐字推送到客户端。
    """
    return StreamingResponse(
        stream_chat_request(request, raw_request.headers),
        media_type="text/event-stream",
    )
