from fastapi import APIRouter, Request

from app.api.auth import resolve_request_user_id
from app.api.serializers import to_api_model
from app.application.run_service import run_service


router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.get("")
def list_inbox(request: Request) -> list[dict]:
    user_id = resolve_request_user_id(request)
    return to_api_model([item.model_dump(mode="json") for item in run_service.list_inbox(user_id)])
