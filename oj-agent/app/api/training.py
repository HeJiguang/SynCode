from fastapi import APIRouter, HTTPException

from app.schemas.training_plan_request import TrainingPlanRequest
from app.schemas.training_plan_response import TrainingPlanResponse
from app.services.training_planner import build_training_plan


router = APIRouter(prefix="/api/training", tags=["training"])


@router.post("/plan", response_model=TrainingPlanResponse)
def training_plan(request: TrainingPlanRequest) -> TrainingPlanResponse:
    try:
        return build_training_plan(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
