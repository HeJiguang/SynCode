from fastapi import APIRouter

from app.runtime.engine import execute_training_plan_request
from app.schemas.training_plan_request import TrainingPlanRequest
from app.schemas.training_plan_response import TrainingPlanResponse


# 定义训练模块的路由，所有接口路径前缀为 /api/training，并在 API 文档中归类为 "training"
router = APIRouter(prefix="/api/training", tags=["training"])


@router.post("/plan", response_model=TrainingPlanResponse)
def training_plan(request: TrainingPlanRequest) -> TrainingPlanResponse:
    """
    训练计划生成接口：根据用户的请求参数，调用后台 AI 引擎生成定制化的训练（如刷题/学习）计划。
    最后将引擎返回的字典或 JSON 载荷，通过 Pydantic (model_validate) 严格校验并转换为标准的返回值模型对象返回。
    """
    state = execute_training_plan_request(request)
    return TrainingPlanResponse.model_validate(state.outcome.response_payload)
