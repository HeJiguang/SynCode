from fastapi import APIRouter, HTTPException, Request, status

from app.api.auth import assert_owned_user, resolve_request_user_id
from app.api.serializers import to_api_model
from app.application.run_service import run_service
from app.schemas.run_api import DraftActionRequest


router = APIRouter(prefix="/api/drafts", tags=["drafts"])


@router.post("/{draft_id}/approve")
def approve_draft(draft_id: str, request: DraftActionRequest, raw_request: Request) -> dict:
    try:
        draft = run_service.get_draft(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="草案不存在。") from exc
    assert_owned_user(draft.user_id, resolve_request_user_id(raw_request, request.user_id))
    return to_api_model(run_service.approve_draft(draft_id).model_dump(mode="json"))


@router.post("/{draft_id}/reject")
def reject_draft(draft_id: str, request: DraftActionRequest, raw_request: Request) -> dict:
    try:
        draft = run_service.get_draft(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="草案不存在。") from exc
    assert_owned_user(draft.user_id, resolve_request_user_id(raw_request, request.user_id))
    return to_api_model(run_service.reject_draft(draft_id).model_dump(mode="json"))
