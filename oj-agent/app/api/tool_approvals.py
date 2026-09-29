from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.auth import resolve_request_user_id
from app.api.serializers import to_api_model
from app.application.run_execution import (
    build_approval_continuation_request,
    execute_and_record_run,
    execute_run_request,
)
from app.application.run_admission import run_execution_slot_limiter, RunExecutionSlotTimeout
from app.conversations import get_conversation_service
from app.application.run_service import run_service
from app.domain.runs import RunStatus
from app.domain.tool_permissions import ToolApprovalStatus
from app.integrations import GitHubRepositoryError


router = APIRouter(prefix="/api/tool-approvals", tags=["tool-approvals"])


@router.get("")
def list_tool_approvals(
    raw_request: Request,
    run_id: str | None = Query(default=None, alias="runId"),
    conversation_id: str | None = Query(default=None, alias="conversationId"),
) -> list[dict]:
    user_id = resolve_request_user_id(raw_request)
    try:
        approvals = get_conversation_service().list_tool_approvals(
            user_id,
            run_id=run_id,
            conversation_id=conversation_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat 不存在。") from exc
    return to_api_model([approval.model_dump(mode="json") for approval in approvals])


@router.post("/{approval_id}/approve")
def approve_tool(approval_id: str, raw_request: Request) -> dict:
    user_id = resolve_request_user_id(raw_request)
    try:
        approval = get_conversation_service().approve_tool(user_id, approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批不存在。") from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except (ValueError, PermissionError, NotImplementedError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except GitHubRepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    _resume_run_if_resolved(user_id, approval.run_id, raw_request)
    return to_api_model(approval.model_dump(mode="json"))


@router.post("/{approval_id}/deny")
def deny_tool(approval_id: str, raw_request: Request) -> dict:
    user_id = resolve_request_user_id(raw_request)
    try:
        approval = get_conversation_service().deny_tool(user_id, approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批不存在。") from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    _resume_run_if_resolved(user_id, approval.run_id, raw_request)
    return to_api_model(approval.model_dump(mode="json"))


def _resume_run_if_resolved(user_id: str, run_id: str, raw_request: Request) -> None:
    conversation_service = get_conversation_service()
    approvals = conversation_service.list_tool_approvals(user_id, run_id=run_id)
    pending = [
        approval
        for approval in approvals
        if approval.status is ToolApprovalStatus.PENDING
    ]
    if pending:
        return
    try:
        run = run_service.get_run(run_id)
    except KeyError:
        return
    if run.user_id != user_id or run.status is not RunStatus.WAITING_USER or not run.conversation_id:
        return
    denied = any(
        approval.status in {ToolApprovalStatus.DENIED, ToolApprovalStatus.EXPIRED}
        for approval in approvals
    )
    with conversation_service.serialized(run.conversation_id, user_id):
        run = run_service.get_run(run_id)
        if run.status is not RunStatus.WAITING_USER:
            return
        continuation = build_approval_continuation_request(
            run,
            user_id=user_id,
            denied=denied,
            conversation_service=conversation_service,
        )
        try:
            with run_execution_slot_limiter.slot():
                execute_and_record_run(
                    continuation,
                    run=run,
                    user_id=user_id,
                    headers=raw_request.headers,
                    continuation=True,
                    executor=execute_run_request,
                    conversation_service=conversation_service,
                )
        except RunExecutionSlotTimeout as exc:
            run_service.mark_failed(
                run.run_id,
                reason=str(exc),
                active_node="run_execution_slot",
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
                headers={"Retry-After": str(exc.retry_after_seconds)},
            ) from exc
