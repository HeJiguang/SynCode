from collections.abc import Mapping
from uuid import uuid4

from fastapi import HTTPException, status

from app.schemas.chat_request import ChatRequest


def normalize_chat_request(request: ChatRequest, headers: Mapping[str, str | None], user_id_header: str) -> ChatRequest:
    """
    规范化聊天请求对象 (Normalize Chat Request)
    
    主要职责：
    1. 身份解析：尝试从请求体或 HTTP Headers 中提取用户 ID。
    2. 链路追踪：确保每个请求都有一个唯一的 Trace ID，用于日志排查。
    3. 数据不可变性：返回一个新的请求对象，而不是修改原始对象。
    """
    
    # 1. 解析用户 ID (User ID Resolution)
    # 优先级：优先使用请求体 (request payload) 中自带的 user_id。
    # 如果请求体中没有，则尝试从 HTTP Headers 中获取（通常由 API 网关在鉴权后注入，比如 "X-User-Id"）。
    resolved_user_id = request.user_id or headers.get(user_id_header)
    
    # 防御性拦截：如果两边都没有用户 ID，说明这是个非法/未登录的请求，直接抛出 401 未授权异常。
    # FastAPI 会自动捕获这个 HTTPException 并向客户端返回标准的 401 错误响应。
    if not resolved_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authenticated user id")

    # 2. 解析/生成链路追踪 ID (Trace ID)
    # 分布式系统排障神器：如果客户端传了 trace_id，就用客户端的；
    # 如果没传，系统在这里自动生成一个标准的 UUID v4。
    # 这样后续所有的日志打点、数据库查询、大模型调用都可以带上这个 ID，方便在一堆乱如麻的日志中串起整个请求轨迹。
    resolved_trace_id = request.trace_id or str(uuid4())
    
    # 3. 返回规范化后的新对象 (Return Immutable Copy)
    # 核心细节：这里使用了 Pydantic V2 的 `model_copy(update={...})` 方法。
    # 它不会直接修改传入的 request 对象（避免产生副作用），而是创建并返回一个应用了新数据的全新副本。
    # 这在函数式编程中是非常优良的实践，能避免很多因为共享引用导致的 Bug。
    return request.model_copy(
        update={
            "user_id": str(resolved_user_id),  # 确保转型为字符串格式
            "trace_id": resolved_trace_id,
        }
    )