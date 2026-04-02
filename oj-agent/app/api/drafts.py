from fastapi import APIRouter

from app.api.serializers import to_api_model
from app.application.run_service import run_service
from app.schemas.run_api import DraftActionRequest


router = APIRouter(prefix="/api/drafts", tags=["drafts"])


@router.post("/{draft_id}/approve")
def approve_draft(draft_id: str, request: DraftActionRequest) -> dict:
    del request
    return to_api_model(run_service.approve_draft(draft_id).model_dump(mode="json"))


@router.post("/{draft_id}/reject")
def reject_draft(draft_id: str, request: DraftActionRequest) -> dict:
    del request
    return to_api_model(run_service.reject_draft(draft_id).model_dump(mode="json"))
