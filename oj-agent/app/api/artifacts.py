from fastapi import APIRouter

from app.api.serializers import to_api_model
from app.application.run_service import run_service


router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("/{run_id}")
def list_artifacts(run_id: str) -> list[dict]:
    return to_api_model([artifact.model_dump(mode="json") for artifact in run_service.list_artifacts(run_id)])
