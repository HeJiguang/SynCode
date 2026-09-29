from app.runtime.enums import TaskType
from app.runtime.models import RequestContext


def build_request_context(
    *,
    trace_id: str,
    user_id: str,
    task_type: TaskType,
    user_message: str,
    conversation_id: str | None = None,
    question_id: str | None = None,
    question_title: str | None = None,
    question_content: str | None = None,
    user_code: str | None = None,
    selected_code: str | None = None,
    language: str | None = None,
    judge_result: str | None = None,
    approved_memories: list[str] | None = None,
    approved_tool_context: list[dict] | None = None,
    exam_id: str | None = None,
    plan_id: str | None = None,
) -> RequestContext:
    return RequestContext(
        trace_id=trace_id,
        user_id=user_id,
        task_type=task_type,
        user_message=user_message,
        conversation_id=conversation_id,
        question_id=question_id,
        question_title=question_title,
        question_content=question_content,
        user_code=user_code,
        selected_code=selected_code,
        language=language,
        judge_result=judge_result,
        approved_memories=list(approved_memories or []),
        approved_tool_context=list(approved_tool_context or []),
        exam_id=exam_id,
        plan_id=plan_id,
    )
