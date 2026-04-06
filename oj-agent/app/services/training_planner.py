from app.schemas.training_plan_request import TrainingPlanRequest
from app.schemas.training_plan_response import TrainingPlanResponse
from app.services.llm_runtime_service import build_training_plan as build_training_plan_with_llm


def build_training_plan(request: TrainingPlanRequest) -> TrainingPlanResponse:
    return build_training_plan_with_llm(request)
