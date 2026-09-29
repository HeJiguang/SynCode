from fastapi import APIRouter, HTTPException, Request, status

from app.api.auth import assert_owned_user, resolve_request_user_id
from app.api.serializers import to_api_model
from app.application.run_service import run_service


router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("/{run_id}")
def list_artifacts(run_id: str, raw_request: Request) -> list[dict]:
    try:
        run = run_service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run 不存在。") from exc
    assert_owned_user(run.user_id, resolve_request_user_id(raw_request))
    return to_api_model([artifact.model_dump(mode="json") for artifact in run_service.list_artifacts(run_id)])
