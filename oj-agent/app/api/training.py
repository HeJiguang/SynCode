from fastapi import APIRouter, HTTPException

from app.runtime.engine import execute_training_plan_request
from app.schemas.training_plan_request import TrainingPlanRequest
from app.schemas.training_plan_response import TrainingPlanResponse


router = APIRouter(prefix="/api/training", tags=["training"])


@router.post("/plan", response_model=TrainingPlanResponse)
def training_plan(request: TrainingPlanRequest) -> TrainingPlanResponse:
    """通过大模型生成结构化训练计划。"""
    try:
        state = execute_training_plan_request(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return TrainingPlanResponse.model_validate(state.outcome.response_payload)
