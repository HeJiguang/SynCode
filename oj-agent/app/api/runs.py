import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.api.serializers import to_api_model
from app.application.run_execution import execute_run_request, should_execute_runtime
from app.application.run_labels import enrich_artifact_model, enrich_run_event_model, enrich_run_model
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


router = APIRouter(prefix="/api/runs", tags=["runs"])


def _parse_run_type(raw: str) -> RunType:
    return RunType(raw)


def _parse_run_source(raw: str) -> RunSource:
    return RunSource(raw)


def _resolve_user_id(request: CreateRunRequest, raw_request: Request) -> str:
    if request.user_id:
        return request.user_id

    header_name = load_settings().gateway_user_id_header
    return raw_request.headers.get(header_name, "") or "workspace-user"


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

    artifact = run_service.add_artifact(_bootstrap_artifact(request, run.run_id))

    if should_execute_runtime(request.run_type):
        try:
            run_service.mark_running(run.run_id, active_node="llm_prepare")
            state = execute_run_request(
                request,
                user_id=user_id,
                trace_id=run.trace_id,
                headers=raw_request.headers,
            )
            project_runtime_events(run.run_id, state, append_event=run_service.append_event)
            run_service.add_artifact(build_runtime_artifact(run.run_id, state))
            register_runtime_write_intents(
                run.run_id,
                user_id,
                state,
                register_write_intent=run_service.register_write_intent,
            )
            run_service.mark_succeeded(run.run_id, active_node=state.execution.active_node)
            run = run_service.get_run(run.run_id)
        except Exception as exc:
            run_service.add_artifact(build_failure_artifact(run.run_id, message=str(exc)))
            run_service.mark_failed(run.run_id, reason=str(exc), active_node="llm_runtime")
            run = run_service.get_run(run.run_id)

    return to_api_model(
        enrich_run_model(
            {
                "run_id": run.run_id,
                "status": run.status.value,
                "entry_graph": run.entry_graph,
                "events_url": f"/api/runs/{run.run_id}/events",
                "artifacts_url": f"/api/runs/{run.run_id}/artifacts",
                "bootstrap_artifact_id": artifact.artifact_id,
            }
        )
    )


@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    return to_api_model(enrich_run_model(run_service.get_run(run_id).model_dump(mode="json")))


@router.get("/{run_id}/events")
def stream_run_events(run_id: str) -> StreamingResponse:
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
def list_run_artifacts(run_id: str) -> list[dict]:
    return to_api_model(
        [enrich_artifact_model(artifact.model_dump(mode="json")) for artifact in run_service.list_artifacts(run_id)]
    )
