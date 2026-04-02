from fastapi import APIRouter

from app.runtime.engine import execute_training_plan_request
from app.schemas.training_plan_request import TrainingPlanRequest
from app.schemas.training_plan_response import TrainingPlanResponse


router = APIRouter(prefix="/api/training", tags=["training"])


@router.post("/plan", response_model=TrainingPlanResponse)
def training_plan(request: TrainingPlanRequest) -> TrainingPlanResponse:
    """Build a structured training plan through the graph runtime."""
    state = execute_training_plan_request(request)
    return TrainingPlanResponse.model_validate(state.outcome.response_payload)
