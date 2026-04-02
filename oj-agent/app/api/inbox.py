from fastapi import APIRouter

from app.api.serializers import to_api_model
from app.application.run_service import run_service


router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.get("")
def list_inbox(user_id: str) -> list[dict]:
    return to_api_model([item.model_dump(mode="json") for item in run_service.list_inbox(user_id)])
