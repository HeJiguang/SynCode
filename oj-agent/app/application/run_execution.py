from collections.abc import Callable, Mapping

from app.api.serializers import to_api_model
from app.application.run_labels import enrich_artifact_model
from app.application.run_projection import (
    build_failure_artifact,
    build_runtime_artifact,
    project_runtime_events,
    register_runtime_write_intents,
)
from app.application.run_service import RunService, run_service
from app.conversations import ConversationService, get_conversation_service
from app.core.config import load_settings
from app.domain.runs import Run, RunType
from app.domain.tool_permissions import ToolApprovalStatus
from app.integrations.learning_tools import LearningToolGateway
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

RunExecutor = Callable[..., UnifiedAgentState]
APPROVED_TOOL_CONTINUATION = (
    "工具审批已完成。请使用 approved_tool_context 继续原任务并直接给出结果，"
    "不要再次请求已经批准或拒绝过的相同工具。"
)
DENIED_TOOL_CONTINUATION = (
    "工具请求已被用户拒绝。请在不使用该工具的前提下继续原任务，明确说明限制并给出仍可执行的建议，"
    "不要再次请求相同工具。"
)


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
    context = build_request_context_from_run(request, user_id=user_id, trace_id=trace_id)
    settings = load_settings()
    authorization = (headers.get("Authorization") or "").strip()
    if settings.auth_base_url and authorization:
        learning = LearningToolGateway(settings.auth_base_url, authorization).collect(
            question_id=context.question_id,
            include_candidates=run_type is RunType.INTERACTIVE_RECOMMENDATION,
        )
        context.learning_context = learning.prompt_data()
        context.learning_tool_calls = learning.calls
    return execute_request_context(context, headers=headers)


def execute_and_record_run(
    request: CreateRunRequest,
    *,
    run: Run,
    user_id: str,
    headers: Mapping[str, str | None],
    continuation: bool = False,
    executor: RunExecutor = execute_run_request,
    service: RunService = run_service,
    conversation_service: ConversationService | None = None,
) -> Run:
    """Execute one Agent turn and durably project all user-visible results."""
    conversations = conversation_service or get_conversation_service()
    conversation_id = run.conversation_id or request.conversation_id
    if not conversation_id:
        raise ValueError("Run 缺少 Chat，无法执行。")

    try:
        service.mark_running(
            run.run_id,
            active_node="tool_context_resume" if continuation else "llm_prepare",
        )
        trace_id = f"{run.trace_id}:resume" if continuation else run.trace_id
        state = executor(
            request,
            user_id=user_id,
            trace_id=trace_id,
            headers=headers,
        )
        runtime_tool_decisions = state.outcome.response_payload.get("runtime_tool_decisions")
        if isinstance(runtime_tool_decisions, list):
            conversations.record_runtime_tool_decisions(
                user_id,
                conversation_id,
                run.run_id,
                runtime_tool_decisions,
            )
        model_tool_requests = state.outcome.response_payload.get("tool_requests")
        tool_approvals = (
            conversations.record_model_tool_requests(
                user_id,
                conversation_id,
                run.run_id,
                model_tool_requests,
                suppress_resolved_duplicates=continuation,
            )
            if isinstance(model_tool_requests, list)
            else []
        )
        state.outcome.response_payload["tool_approvals"] = to_api_model(
            [approval.model_dump(mode="json") for approval in tool_approvals]
        )
        project_runtime_events(run.run_id, state, append_event=service.append_event)
        runtime_artifact = service.add_artifact(build_runtime_artifact(run.run_id, state))
        assistant_message = conversations.append_assistant_message(
            conversation_id,
            user_id,
            content=state.outcome.answer or "",
            run_id=run.run_id,
            question_id=request.context.question_id,
            question_title=request.context.question_title,
            artifact=to_api_model(enrich_artifact_model(runtime_artifact.model_dump(mode="json"))),
        )
        candidates = state.outcome.response_payload.get("memory_candidates")
        if isinstance(candidates, list):
            conversations.record_memory_candidates(
                user_id,
                conversation_id,
                assistant_message.message_id,
                candidates,
            )
        register_runtime_write_intents(
            run.run_id,
            user_id,
            state,
            register_write_intent=service.register_write_intent,
        )
        pending_approvals = [
            approval.approval_id
            for approval in tool_approvals
            if approval.status is ToolApprovalStatus.PENDING
        ]
        if pending_approvals:
            service.mark_waiting_user(run.run_id, approval_ids=pending_approvals)
        else:
            service.mark_succeeded(run.run_id, active_node=state.execution.active_node)
    except Exception as exc:
        failure_artifact = service.add_artifact(build_failure_artifact(run.run_id, message=str(exc)))
        conversations.append_assistant_message(
            conversation_id,
            user_id,
            content=str(exc),
            run_id=run.run_id,
            question_id=request.context.question_id,
            question_title=request.context.question_title,
            artifact=to_api_model(enrich_artifact_model(failure_artifact.model_dump(mode="json"))),
            failed=True,
        )
        service.mark_failed(run.run_id, reason=str(exc), active_node="llm_runtime")
    return service.get_run(run.run_id)


def build_approval_continuation_request(
    run: Run,
    *,
    user_id: str,
    denied: bool,
    conversation_service: ConversationService | None = None,
) -> CreateRunRequest:
    """Rehydrate the original request and attach the latest reviewed tool context."""
    if not run.request_payload:
        raise ValueError("Run 缺少原始请求快照，无法在审批后恢复。")
    request = CreateRunRequest.model_validate(run.request_payload)
    if not run.conversation_id:
        raise ValueError("Run 缺少 Chat，无法在审批后恢复。")
    conversations = conversation_service or get_conversation_service()
    request.user_id = user_id
    request.conversation_id = run.conversation_id
    request.context.approved_memories = [
        memory.content
        for memory in conversations.context_memories(run.conversation_id, user_id)
    ]
    request.context.approved_tool_context = conversations.active_tool_context(
        run.conversation_id,
        user_id,
    )
    original_message = (request.context.user_message or "").strip()
    continuation_instruction = DENIED_TOOL_CONTINUATION if denied else APPROVED_TOOL_CONTINUATION
    request.context.user_message = "\n".join(
        [continuation_instruction, f"原始用户请求：{original_message}"]
    )
    return request


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
        selected_code=context.selected_code,
        language=context.language,
        judge_result=context.judge_result,
        approved_memories=context.approved_memories,
        approved_tool_context=context.approved_tool_context,
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
        conversation_id=request.conversation_id,
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
        return "请帮我诊断最近一次失败。"
    if run_type is RunType.INTERACTIVE_RECOMMENDATION:
        return "请推荐下一步练习。"
    if run_type is RunType.INTERACTIVE_REVIEW:
        return "请复盘我最近的练习，并总结下一步。"
    return "请帮助我解决当前工作区里的问题。"


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
