import json
from typing import Any

from app.agent_runtime import AgentRunRequest, build_agent_runtime
from app.llm.base import TRAINING_CAPABILITY
from app.schemas.training_plan_request import TrainingPlanRequest
from app.schemas.training_plan_response import TrainingPlanResponse


def build_training_plan(request: TrainingPlanRequest) -> TrainingPlanResponse:
    runtime = build_agent_runtime()
    _result, payload = runtime.generate_json(
        AgentRunRequest(
            system_prompt=_system_prompt(),
            user_prompt=_user_prompt(request),
            capability=TRAINING_CAPABILITY,
            user_id=str(request.user_id),
            trace_id=request.trace_id,
            conversation_id=request.conversation_id,
        )
    )
    return _normalize_payload(request, payload)


def _system_prompt() -> str:
    return "\n".join(
        [
            "你是 OnlineOJ 的训练计划智能体。",
            "必须返回严格 JSON，不要输出额外说明。",
            "所有字段语义必须是中文，但键名保持请求要求中的英文。",
            "任务只能从给定的 candidate_questions 和 candidate_exams 中选择。",
            "如果无法生成合法计划，直接返回空 tasks，不要编造不存在的题目或考试。",
        ]
    )


def _user_prompt(request: TrainingPlanRequest) -> str:
    return "\n".join(
        [
            "请生成 TrainingPlanResponse 结构的 JSON：",
            "字段包括 current_level, target_direction, weak_points, strong_points, plan_title, plan_goal, ai_summary, tasks。",
            "tasks 中每项必须包含 task_type, question_id, exam_id, title_snapshot, task_order, recommended_reason, knowledge_tags_snapshot, due_time。",
            "允许的 task_type 仅为 review, question, test。",
            json.dumps(request.model_dump(mode="json", by_alias=True), ensure_ascii=False),
        ]
    )


def _normalize_payload(request: TrainingPlanRequest, payload: dict[str, Any]) -> TrainingPlanResponse:
    allowed_question_ids = {candidate.question_id for candidate in request.candidate_questions}
    allowed_exam_ids = {candidate.exam_id for candidate in request.candidate_exams}
    if request.based_on_exam_id is not None:
        allowed_exam_ids.add(request.based_on_exam_id)

    tasks: list[dict[str, Any]] = []
    raw_tasks = payload.get("tasks")
    for index, raw in enumerate(raw_tasks if isinstance(raw_tasks, list) else [], start=1):
        if not isinstance(raw, dict):
            continue
        task_type = _text(raw.get("task_type")) or "question"
        question_id = raw.get("question_id")
        exam_id = raw.get("exam_id")
        if task_type == "test":
            if exam_id not in allowed_exam_ids:
                continue
            question_id = None
        else:
            if question_id not in allowed_question_ids:
                continue
            exam_id = None
        tasks.append(
            {
                "task_type": task_type,
                "question_id": question_id,
                "exam_id": exam_id,
                "title_snapshot": _text(raw.get("title_snapshot")) or f"训练任务 {index}",
                "task_order": raw.get("task_order") or index,
                "recommended_reason": _text(raw.get("recommended_reason")) or "围绕你当前阶段的重点进行安排。",
                "knowledge_tags_snapshot": _text(raw.get("knowledge_tags_snapshot")),
                "due_time": raw.get("due_time"),
            }
        )

    if not tasks:
        raise RuntimeError("大模型没有生成可用的训练计划任务。")

    return TrainingPlanResponse.model_validate(
        {
            "current_level": _text(payload.get("current_level")) or request.current_level or "starter",
            "target_direction": _text(payload.get("target_direction")) or request.target_direction or "algorithm_foundation",
            "weak_points": _text(payload.get("weak_points")) or "待通过训练计划进一步定位。",
            "strong_points": _text(payload.get("strong_points")) or "待通过训练计划进一步总结。",
            "plan_title": _text(payload.get("plan_title")) or "个性化训练计划",
            "plan_goal": _text(payload.get("plan_goal")) or "围绕当前阶段的薄弱点进行强化训练。",
            "ai_summary": _text(payload.get("ai_summary")) or "已根据当前上下文生成一份可执行的训练计划。",
            "tasks": tasks,
        }
    )


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        return "、".join(part for item in value if (part := _text(item)))
    if isinstance(value, dict):
        return _text(value.get("text") or value.get("summary") or value.get("value"))
    return str(value).strip()
