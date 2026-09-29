import json

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.serializers import to_api_model
from app.api.auth import assert_owned_user, resolve_request_user_id
from app.application.run_admission import (
    RunAdmissionError,
    RunExecutionSlotTimeout,
    create_admitted_run,
    run_execution_slot_limiter,
)
from app.application.run_execution import execute_and_record_run, execute_run_request, should_execute_runtime
from app.application.run_labels import enrich_artifact_model, enrich_run_event_model, enrich_run_model
from app.application.run_service import run_service
from app.conversations import get_conversation_service
from app.conversations.service import ConversationLimitReached
from app.domain.artifacts import Artifact, ArtifactType, RenderHint
from app.domain.runs import ContextRef, EventType, RunSource, RunStatus, RunType
from app.schemas.run_api import CreateRunRequest


router = APIRouter(prefix="/api/runs", tags=["runs"])


def _parse_run_type(raw: str) -> RunType:
    return RunType(raw)


def _parse_run_source(raw: str) -> RunSource:
    return RunSource(raw)


def _resolve_user_id(request: CreateRunRequest, raw_request: Request) -> str:
    return resolve_request_user_id(raw_request, request.user_id)


def _bootstrap_artifact(request: CreateRunRequest, run_id: str) -> Artifact:
    title = "智能体任务已创建"
    summary = "本次运行已创建，正在准备执行。"
    if request.run_type == RunType.INTERACTIVE_DIAGNOSIS.value:
        title = "诊断任务已创建"
        summary = "正在分析最近一次失败上下文。"
    elif request.run_type == RunType.INTERACTIVE_PLAN.value:
        title = "规划任务已创建"
        summary = "正在生成或重算训练计划。"

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


@router.post("")
def create_run(request: CreateRunRequest, raw_request: Request) -> dict:
    user_id = _resolve_user_id(request, raw_request)
    request.user_id = user_id
    conversation_service = get_conversation_service()
    try:
        if request.conversation_id:
            conversation = conversation_service.ensure_can_continue(request.conversation_id, user_id)
        else:
            conversation = conversation_service.get_default(user_id).conversation
        request.conversation_id = conversation.conversation_id
        request.context.approved_memories = [
            memory.content
            for memory in conversation_service.context_memories(conversation.conversation_id, user_id)
        ]
        request.context.approved_tool_context = conversation_service.active_tool_context(
            conversation.conversation_id,
            user_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat 不存在。") from exc
    except ConversationLimitReached as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    with conversation_service.serialized(conversation.conversation_id, user_id):
        try:
            conversation_service.ensure_can_continue(conversation.conversation_id, user_id)
        except ConversationLimitReached as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        try:
            run = create_admitted_run(
                run_service,
                run_type=_parse_run_type(request.run_type),
                source=_parse_run_source(request.source),
                user_id=user_id,
                conversation_id=request.conversation_id,
                context_ref=ContextRef(
                    question_id=request.context.question_id,
                    submission_id=request.context.submission_id,
                ),
                request_payload=request.model_dump(mode="json"),
                queue_for_execution=should_execute_runtime(request.run_type),
            )
        except RunAdmissionError as exc:
            headers = {"Retry-After": str(exc.retry_after_seconds)} if exc.retry_after_seconds else None
            raise HTTPException(
                status_code=exc.status_code,
                detail=str(exc),
                headers=headers,
            ) from exc
        except TimeoutError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        artifact = run_service.add_artifact(_bootstrap_artifact(request, run.run_id))
        context_snapshot = request.context.model_dump(mode="json", exclude={"user_message", "approved_memories"})
        conversation_service.append_user_message(
            conversation.conversation_id,
            user_id,
            content=request.context.user_message or "",
            run_id=run.run_id,
            question_id=request.context.question_id,
            question_title=request.context.question_title,
            context_snapshot=context_snapshot,
        )

        if should_execute_runtime(request.run_type):
            try:
                with run_execution_slot_limiter.slot():
                    run = execute_and_record_run(
                        request,
                        run=run,
                        user_id=user_id,
                        headers=raw_request.headers,
                        executor=execute_run_request,
                        conversation_service=conversation_service,
                    )
            except RunExecutionSlotTimeout as exc:
                run = run_service.mark_failed(
                    run.run_id,
                    reason=str(exc),
                    active_node="run_execution_slot",
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=str(exc),
                    headers={"Retry-After": str(exc.retry_after_seconds)},
                ) from exc

        latest_conversation = conversation_service.get_snapshot(conversation.conversation_id, user_id).conversation
        return to_api_model(
            enrich_run_model(
                {
                    "run_id": run.run_id,
                    "status": run.status.value,
                    "entry_graph": run.entry_graph,
                    "events_url": f"/api/runs/{run.run_id}/events",
                    "artifacts_url": f"/api/runs/{run.run_id}/artifacts",
                    "bootstrap_artifact_id": artifact.artifact_id,
                    "conversation_id": conversation.conversation_id,
                    "rollover_recommended": latest_conversation.rollover_recommended,
                    "context_token_estimate": latest_conversation.context_token_estimate,
                    "context_token_limit": latest_conversation.hard_token_limit,
                }
            )
        )


@router.get("/{run_id}")
def get_run(run_id: str, raw_request: Request) -> dict:
    try:
        run = run_service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run 不存在。") from exc
    assert_owned_user(run.user_id, resolve_request_user_id(raw_request))
    return to_api_model(
        enrich_run_model(run.model_dump(mode="json", exclude={"request_payload"}))
    )


@router.post("/{run_id}/recommendations/{question_id}/{action}")
def record_recommendation_interaction(run_id: str, question_id: str, action: str, raw_request: Request) -> dict:
    if action not in {"impression", "click"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="推荐事件不存在。")
    try:
        run = run_service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run 不存在。") from exc
    assert_owned_user(run.user_id, resolve_request_user_id(raw_request))
    if run.status is not RunStatus.SUCCEEDED or run.run_type is not RunType.INTERACTIVE_RECOMMENDATION:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="推荐结果尚不可用。")
    recommendations = [
        item
        for artifact in run_service.list_artifacts(run_id)
        for item in (artifact.body.get("responsePayload") or {}).get("recommendations", [])
        if isinstance(item, dict)
    ]
    if not any(str(item.get("question_id")) == question_id for item in recommendations):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="推荐题目不存在。")
    event_type = EventType.RECOMMENDATION_IMPRESSION if action == "impression" else EventType.RECOMMENDATION_CLICKED
    if not any(
        event.event_type is event_type and event.payload.get("questionId") == question_id
        for event in run_service.list_events(run_id)
    ):
        run_service.append_event(run_id, event_type, {"questionId": question_id})
    return {"recorded": True}


@router.get("/{run_id}/events")
def stream_run_events(run_id: str, raw_request: Request) -> StreamingResponse:
    try:
        run = run_service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run 不存在。") from exc
    assert_owned_user(run.user_id, resolve_request_user_id(raw_request))
    events = run_service.list_events(run_id)

    def _event_stream():
        for event in events:
            payload = json.dumps(
                to_api_model(enrich_run_event_model(event.model_dump(mode="json"))),
                ensure_ascii=False,
            )
            yield f"event: run_event\ndata: {payload}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@router.get("/{run_id}/artifacts")
def list_run_artifacts(run_id: str, raw_request: Request) -> list[dict]:
    try:
        run = run_service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run 不存在。") from exc
    assert_owned_user(run.user_id, resolve_request_user_id(raw_request))
    return to_api_model(
        [enrich_artifact_model(artifact.model_dump(mode="json")) for artifact in run_service.list_artifacts(run_id)]
    )
