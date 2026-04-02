import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

# 导入业务逻辑相关的序列化工具、执行函数、投射工具和基础服务
from app.api.serializers import to_api_model
from app.application.run_execution import execute_run_request, should_execute_runtime
from app.application.run_projection import (
    build_failure_artifact,
    build_runtime_artifact,
    project_runtime_events,
    register_runtime_write_intents,
)
from app.application.run_service import run_service
from app.core.config import load_settings
from app.domain.artifacts import Artifact, ArtifactType, RenderHint
from app.domain.runs import ContextRef, RunSource, RunType
from app.schemas.run_api import CreateRunRequest

# 初始化路由对象，设置前缀为 /api/runs，并打上 "runs" 标签
router = APIRouter(prefix="/api/runs", tags=["runs"])

# 内部工具函数：将字符串转换为运行类型枚举
def _parse_run_type(raw: str) -> RunType:
    return RunType(raw)

# 内部工具函数：将字符串转换为运行来源枚举
def _parse_run_source(raw: str) -> RunSource:
    return RunSource(raw)

# 内部工具函数：解析用户 ID。优先用请求体里的，没有则从 HTTP Header 取，最后兜底
def _resolve_user_id(request: CreateRunRequest, raw_request: Request) -> str:
    if request.user_id:
        return request.user_id

    header_name = load_settings().gateway_user_id_header
    return raw_request.headers.get(header_name, "") or "workspace-user"

# 内部工具函数：初始化一个“引导工件（Artifact）”，即任务开始时的 UI 展现信息
def _bootstrap_artifact(request: CreateRunRequest, run_id: str) -> Artifact:
    title = "Agent run initialized"
    summary = "The run was created and is ready for graph execution."
    # 根据不同的运行类型（诊断或规划），设置不同的标题和摘要
    if request.run_type == RunType.INTERACTIVE_DIAGNOSIS.value:
        title = "Diagnosis run initialized"
        summary = "The runtime will analyze the latest failure context."
    elif request.run_type == RunType.INTERACTIVE_PLAN.value:
        title = "Planning run initialized"
        summary = "The runtime will build or recompute a training plan."

    # 返回一个工件对象，定义了如何在前端时间轴（Timeline）上渲染
    return Artifact(
        run_id=run_id,
        artifact_type=ArtifactType.ANSWER_CARD,
        title=title,
        summary=summary,
        body={
            "userMessage": request.context.user_message,
            "questionTitle": request.context.question_title,
            "judgeResult": request.context.judge_result,
        },
        render_hint=RenderHint.TIMELINE_CARD,
    )

# POST 接口：创建一个新的运行任务
@router.post("")
def create_run(request: CreateRunRequest, raw_request: Request) -> dict:
    # 1. 确定操作者 ID
    user_id = _resolve_user_id(request, raw_request)
    
    # 2. 调用服务层在数据库中创建一个运行记录
    run = run_service.create_run(
        run_type=_parse_run_type(request.run_type),
        source=_parse_run_source(request.source),
        user_id=user_id,
        conversation_id=request.conversation_id,
        context_ref=ContextRef(
            question_id=request.context.question_id,
            submission_id=request.context.submission_id,
        ),
    )
    
    # 3. 创建并存储初始化的引导工件
    artifact = run_service.add_artifact(_bootstrap_artifact(request, run.run_id))
    
    # 4. 判断是否需要立即同步执行运行时（Runtime）
    if should_execute_runtime(request.run_type):
        try:
            # 标记状态为运行中，当前节点设为控制台图（supervisor_graph）
            run_service.mark_running(run.run_id, active_node="supervisor_graph")
            
            # 真正开始执行复杂的逻辑（可能是调用 LLM 或工作流）
            state = execute_run_request(
                request,
                user_id=user_id,
                trace_id=run.trace_id,
                headers=raw_request.headers,
            )
            
            # 将执行产生的事件投射（同步）到数据库
            project_runtime_events(run.run_id, state, append_event=run_service.append_event)
            
            # 将最终结果生成为一个工件
            run_service.add_artifact(build_runtime_artifact(run.run_id, state))
            
            # 注册写入意图（可能用于后续的数据库更新或 side effects）
            register_runtime_write_intents(
                run.run_id,
                user_id,
                state,
                register_write_intent=run_service.register_write_intent,
            )
            
            # 标记运行成功
            run_service.mark_succeeded(run.run_id, active_node=state.execution.active_node)
            # 重新获取最新的运行对象
            run = run_service.get_run(run.run_id)
            
        except Exception as exc:
            # 如果中途报错，记录错误工件并标记为失败
            run_service.add_artifact(build_failure_artifact(run.run_id, message=str(exc)))
            run_service.mark_failed(run.run_id, reason=str(exc), active_node="runtime_execution")
            run = run_service.get_run(run.run_id)
            
    # 返回 API 定义的模型，包含 ID、状态及相关资源的 URL
    return to_api_model(
        {
            "run_id": run.run_id,
            "status": run.status.value,
            "entry_graph": run.entry_graph,
            "events_url": f"/api/runs/{run.run_id}/events",
            "artifacts_url": f"/api/runs/{run.run_id}/artifacts",
            "bootstrap_artifact_id": artifact.artifact_id,
        }
    )

# GET 接口：根据 ID 获取特定运行的详细信息
@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    return to_api_model(run_service.get_run(run_id).model_dump(mode="json"))

# GET 接口：流式推送（SSE）运行过程中的事件
@router.get("/{run_id}/events")
def stream_run_events(run_id: str) -> StreamingResponse:
    # 从服务层获取该运行的所有事件
    events = run_service.list_events(run_id)

    # 生成器函数：将事件封装成 Server-Sent Events (SSE) 格式
    def _event_stream():
        for event in events:
            # 序列化为 JSON 字符串
            payload = json.dumps(to_api_model(event.model_dump(mode="json")), ensure_ascii=False)
            # 构造标准的 SSE 数据块格式
            yield f"event: run_event\ndata: {payload}\n\n"

    # 返回流式响应，媒体类型为 text/event-stream
    return StreamingResponse(_event_stream(), media_type="text/event-stream")

# GET 接口：列出该运行产生的所有工件（如诊断卡片、结果等）
@router.get("/{run_id}/artifacts")
def list_run_artifacts(run_id: str) -> list[dict]:
    return to_api_model([artifact.model_dump(mode="json") for artifact in run_service.list_artifacts(run_id)])