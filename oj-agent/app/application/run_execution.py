from collections.abc import Mapping

from app.domain.runs import RunType
from app.runtime.context import build_request_context
from app.runtime.engine import execute_request_context, execute_training_plan_request
from app.runtime.enums import TaskType
from app.runtime.models import RequestContext, UnifiedAgentState
from app.schemas.run_api import CreateRunRequest
from app.schemas.training_plan_request import (
    QuestionCandidate,
    SubmissionSnapshot,
    TrainingPlanRequest,
)

# 交互任务，创建后立刻开始运行
INTERACTIVE_RUN_TYPES = {
    RunType.INTERACTIVE_TUTOR,
    RunType.INTERACTIVE_DIAGNOSIS,
    RunType.INTERACTIVE_RECOMMENDATION,
    RunType.INTERACTIVE_REVIEW,
    RunType.INTERACTIVE_PLAN,
}


def should_execute_runtime(run_type: str) -> bool:
    return RunType(run_type) in INTERACTIVE_RUN_TYPES


# 训练计划流程和普通流程的分流
def execute_run_request(
    request: CreateRunRequest,
    *,
    user_id: str,
    trace_id: str,
    headers: Mapping[str, str | None],
) -> UnifiedAgentState:
    run_type = RunType(request.run_type)
    if run_type is RunType.INTERACTIVE_PLAN:
        return execute_training_plan_request(
            build_training_plan_request_from_run(
                request,
                user_id=user_id,
                trace_id=trace_id,
            )
        )
    return execute_request_context(
        build_request_context_from_run(
            request,
            user_id=user_id,
            trace_id=trace_id,
        ),
        headers=headers,
    )


def build_request_context_from_run(
    request: CreateRunRequest,
    *,
    user_id: str,
    trace_id: str,
) -> RequestContext:
    context = request.context
    run_type = RunType(request.run_type)
    return build_request_context(
        trace_id=trace_id,
        user_id=user_id,
        task_type=_task_type_for_run(run_type),
        user_message=context.user_message or _default_prompt_for_run(run_type),
        conversation_id=request.conversation_id,
        question_id=context.question_id,
        question_title=context.question_title,
        question_content=context.question_content,
        user_code=context.user_code,
        judge_result=context.judge_result,
    )


def build_training_plan_request_from_run(
    request: CreateRunRequest,
    *,
    user_id: str,
    trace_id: str,
) -> TrainingPlanRequest:
    context = request.context
    question_id = _coerce_int(context.question_id)
    submission_id = _coerce_int(context.submission_id)
    judge_result = (context.judge_result or "").casefold()
    pass_flag = None
    if judge_result:
        pass_flag = 1 if "accepted" in judge_result else 0

    recent_submissions: list[SubmissionSnapshot] = []
    if question_id is not None or submission_id is not None or context.question_title or context.judge_result:
        recent_submissions.append(
            SubmissionSnapshot(
                submit_id=submission_id,
                question_id=question_id,
                title=context.question_title,
                pass_=pass_flag,
                exe_message=context.judge_result,
            )
        )

    candidate_questions: list[QuestionCandidate] = []
    if question_id is not None and context.question_title:
        candidate_questions.append(
            QuestionCandidate(
                question_id=question_id,
                title=context.question_title,
                knowledge_tags="workspace follow-up",
            )
        )

    return TrainingPlanRequest(
        trace_id=trace_id,
        user_id=_coerce_int(user_id) or 0,
        target_direction="algorithm_foundation",
        recent_submissions=recent_submissions,
        candidate_questions=candidate_questions,
    )


def _task_type_for_run(run_type: RunType) -> TaskType:
    mapping = {
        RunType.INTERACTIVE_TUTOR: TaskType.CHAT,
        RunType.INTERACTIVE_DIAGNOSIS: TaskType.DIAGNOSIS,
        RunType.INTERACTIVE_RECOMMENDATION: TaskType.RECOMMENDATION,
        RunType.INTERACTIVE_REVIEW: TaskType.REVIEW,
    }
    return mapping.get(run_type, TaskType.CHAT)

# 根据不同任务类型，补默认提示
def _default_prompt_for_run(run_type: RunType) -> str:
    if run_type is RunType.INTERACTIVE_DIAGNOSIS:
        return "Help me diagnose the latest failure."
    if run_type is RunType.INTERACTIVE_RECOMMENDATION:
        return "Recommend the next practice step."
    if run_type is RunType.INTERACTIVE_REVIEW:
        return "Review my recent practice and summarize the next step."
    return "Help me with the current workspace problem."


def _coerce_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    candidate = str(raw).strip()
    if not candidate:
        return None
    try:
        return int(candidate)
    except ValueError:
        return None
