import json
from typing import Any

from app.llm.base import CHAT_CAPABILITY, TRAINING_CAPABILITY
from app.llm.factory import build_llm_client
from app.runtime.enums import RiskLevel, RunStatus, TaskType
from app.runtime.models import (
    EvidenceState,
    ExecutionState,
    GuardrailState,
    OutcomeState,
    RequestContext,
    UnifiedAgentState,
    WriteIntent,
)
from app.schemas.training_plan_request import TrainingPlanRequest
from app.schemas.training_plan_response import TrainingPlanResponse


def execute_chat_with_llm(request_context: RequestContext) -> UnifiedAgentState:
    client = build_llm_client()
    payload = client.generate_json(
        system_prompt=_chat_system_prompt(request_context.task_type),
        user_prompt=_chat_user_prompt(request_context),
        capability=CHAT_CAPABILITY,
    )

    answer = _read_string(payload, "answer")
    if not answer:
        raise RuntimeError("大模型没有返回有效回答。")

    next_action = _read_string(payload, "next_action") or _default_next_action(request_context.task_type)
    summary = _read_string(payload, "summary") or _first_line(answer)
    confidence = _read_confidence(payload.get("confidence"))
    intent = _read_string(payload, "intent") or _intent_for_task_type(request_context.task_type)
    title = _read_string(payload, "title") or _title_for_task_type(request_context.task_type)

    execution = ExecutionState(
        run_id=request_context.trace_id,
        graph_name="llm_runtime",
        status=RunStatus.SUCCEEDED,
        active_node="response_packaging",
        model_name=client.model_name(CHAT_CAPABILITY),
    )
    outcome = OutcomeState(
        intent=intent,
        answer=answer,
        next_action=next_action,
        confidence=confidence,
        status_events=[
            {"node": "llm_prepare", "message": "已整理大模型输入上下文。"},
            {"node": "llm_inference", "message": f"已通过模型 {client.model_name(CHAT_CAPABILITY)} 完成推理。"},
            {"node": "response_packaging", "message": "已整理模型输出结果。"},
        ],
        response_payload={
            "title": title,
            "summary": summary,
        },
    )
    return UnifiedAgentState(
        request=request_context,
        execution=execution,
        evidence=EvidenceState(route_names=["llm_only"]),
        guardrail=GuardrailState(
            risk_level=RiskLevel.LOW if _has_core_context(request_context) else RiskLevel.MEDIUM,
            completeness_ok=_has_core_context(request_context),
            policy_ok=True,
        ),
        outcome=outcome,
    )


def execute_training_plan_with_llm(request: TrainingPlanRequest) -> UnifiedAgentState:
    client = build_llm_client()
    payload = client.generate_json(
        system_prompt=_training_system_prompt(),
        user_prompt=_training_user_prompt(request),
        capability=TRAINING_CAPABILITY,
    )
    response = _normalize_training_plan_payload(request, payload)

    request_context = RequestContext(
        trace_id=request.trace_id,
        user_id=str(request.user_id),
        task_type=TaskType.TRAINING_PLAN,
        user_message="生成训练计划。",
    )
    execution = ExecutionState(
        run_id=request.trace_id,
        graph_name="llm_runtime",
        status=RunStatus.SUCCEEDED,
        active_node="training_plan_llm",
        model_name=client.model_name(TRAINING_CAPABILITY),
    )
    outcome = OutcomeState(
        intent="training_plan",
        answer=response.ai_summary,
        next_action="按顺序执行第一项训练任务，然后再回来判断是否需要微调计划。",
        confidence=0.9,
        response_payload=response.model_dump(mode="json"),
        write_intents=[
            WriteIntent(
                intent_type="training_plan_write",
                target_service="oj-friend",
                payload=response.model_dump(mode="json"),
            )
        ],
        status_events=[
            {"node": "llm_prepare", "message": "已整理训练计划生成所需上下文。"},
            {"node": "llm_inference", "message": f"已通过模型 {client.model_name(TRAINING_CAPABILITY)} 生成训练计划。"},
            {"node": "training_plan_llm", "message": "已校验并封装训练计划结果。"},
        ],
    )
    return UnifiedAgentState(
        request=request_context,
        execution=execution,
        evidence=EvidenceState(route_names=["llm_only"]),
        guardrail=GuardrailState(
            risk_level=RiskLevel.LOW,
            completeness_ok=True,
            policy_ok=True,
        ),
        outcome=outcome,
    )


def build_training_plan(request: TrainingPlanRequest) -> TrainingPlanResponse:
    return _normalize_training_plan_payload(
        request,
        build_llm_client().generate_json(
            system_prompt=_training_system_prompt(),
            user_prompt=_training_user_prompt(request),
            capability=TRAINING_CAPABILITY,
        ),
    )


def _chat_system_prompt(task_type: TaskType) -> str:
    return "\n".join(
        [
            "你是 OnlineOJ 的中文原生智能体。",
            "所有输出都必须是中文，并且必须返回 JSON 对象，不要输出 Markdown 代码块。",
            "不要使用规则诊断口吻替代真实分析；如果上下文不足，请明确指出缺失项。",
            "除非用户明确要求完整代码，否则不要直接给完整答案代码。",
            f"当前任务类型：{task_type.value}。",
            "请返回这些字段：intent, title, summary, answer, next_action, confidence。",
            "confidence 取值范围为 0 到 1。",
        ]
    )


def _chat_user_prompt(request_context: RequestContext) -> str:
    payload = {
        "task_type": request_context.task_type.value,
        "question_id": request_context.question_id,
        "question_title": request_context.question_title,
        "question_content": request_context.question_content,
        "user_code": request_context.user_code,
        "judge_result": request_context.judge_result,
        "user_message": request_context.user_message,
    }
    return "\n".join(
        [
            "请基于以下上下文生成回答：",
            json.dumps(payload, ensure_ascii=False),
            "",
            "要求：",
            f"1. intent 优先使用 {_intent_for_task_type(request_context.task_type)}。",
            f"2. title 优先使用 {_title_for_task_type(request_context.task_type)}。",
            "3. answer 要直接回应用户问题。",
            "4. next_action 给出用户现在最值得执行的一步。",
        ]
    )


def _training_system_prompt() -> str:
    return "\n".join(
        [
            "你是 OnlineOJ 的训练计划智能体。",
            "必须返回严格 JSON，不要输出额外说明。",
            "所有字段语义必须是中文，但键名保持请求要求中的英文。",
            "任务只能从给定的 candidate_questions 和 candidate_exams 中选择。",
            "如果无法生成合法计划，直接返回空 tasks，不要编造不存在的题目或考试。",
        ]
    )


def _training_user_prompt(request: TrainingPlanRequest) -> str:
    return "\n".join(
        [
            "请生成 TrainingPlanResponse 结构的 JSON：",
            "字段包括 current_level, target_direction, weak_points, strong_points, plan_title, plan_goal, ai_summary, tasks。",
            "tasks 中每项必须包含 task_type, question_id, exam_id, title_snapshot, task_order, recommended_reason, knowledge_tags_snapshot, due_time。",
            "允许的 task_type 仅为 review, question, test。",
            json.dumps(request.model_dump(mode="json", by_alias=True), ensure_ascii=False),
        ]
    )


def _normalize_training_plan_payload(request: TrainingPlanRequest, payload: dict[str, Any]) -> TrainingPlanResponse:
    allowed_question_ids = {candidate.question_id for candidate in request.candidate_questions}
    allowed_exam_ids = {candidate.exam_id for candidate in request.candidate_exams}
    if request.based_on_exam_id is not None:
        allowed_exam_ids.add(request.based_on_exam_id)

    normalized_tasks: list[dict[str, Any]] = []
    for index, raw_task in enumerate(payload.get("tasks") or [], start=1):
        task_type = str(raw_task.get("task_type") or "").strip() or "question"
        question_id = raw_task.get("question_id")
        exam_id = raw_task.get("exam_id")

        if task_type == "test":
            if exam_id not in allowed_exam_ids:
                continue
            question_id = None
        else:
            if question_id not in allowed_question_ids:
                continue
            exam_id = None

        normalized_tasks.append(
            {
                "task_type": task_type,
                "question_id": question_id,
                "exam_id": exam_id,
                "title_snapshot": _coerce_text(raw_task.get("title_snapshot")) or f"训练任务 {index}",
                "task_order": raw_task.get("task_order") or index,
                "recommended_reason": _coerce_text(raw_task.get("recommended_reason")) or "围绕你当前阶段的重点进行安排。",
                "knowledge_tags_snapshot": _coerce_text(raw_task.get("knowledge_tags_snapshot")),
                "due_time": raw_task.get("due_time"),
            }
        )

    if not normalized_tasks:
        raise RuntimeError("大模型没有生成可用的训练计划任务。")

    return TrainingPlanResponse.model_validate(
        {
            "current_level": _coerce_text(payload.get("current_level")) or request.current_level or "starter",
            "target_direction": _coerce_text(payload.get("target_direction")) or request.target_direction or "algorithm_foundation",
            "weak_points": _coerce_text(payload.get("weak_points")) or "待通过训练计划进一步定位。",
            "strong_points": _coerce_text(payload.get("strong_points")) or "待通过训练计划进一步总结。",
            "plan_title": _coerce_text(payload.get("plan_title")) or "个性化训练计划",
            "plan_goal": _coerce_text(payload.get("plan_goal")) or "围绕当前阶段的薄弱点进行强化训练。",
            "ai_summary": _coerce_text(payload.get("ai_summary")) or "已根据当前上下文生成一份可执行的训练计划。",
            "tasks": normalized_tasks,
        }
    )


def _intent_for_task_type(task_type: TaskType) -> str:
    mapping = {
        TaskType.CHAT: "explain_problem",
        TaskType.DIAGNOSIS: "analyze_failure",
        TaskType.RECOMMENDATION: "recommend_question",
        TaskType.REVIEW: "review_summary",
        TaskType.PROFILE: "profile_update",
        TaskType.TRAINING_PLAN: "training_plan",
    }
    return mapping.get(task_type, "explain_problem")


def _title_for_task_type(task_type: TaskType) -> str:
    mapping = {
        TaskType.CHAT: "解题提示",
        TaskType.DIAGNOSIS: "诊断总结",
        TaskType.RECOMMENDATION: "练习建议",
        TaskType.REVIEW: "复盘总结",
        TaskType.PROFILE: "画像更新",
        TaskType.TRAINING_PLAN: "训练计划",
    }
    return mapping.get(task_type, "智能体回答")


def _default_next_action(task_type: TaskType) -> str:
    mapping = {
        TaskType.CHAT: "先按当前提示梳理题意、核心模式和边界样例，再继续编码。",
        TaskType.DIAGNOSIS: "先复现问题，再对照判题结果逐步定位最早出错的位置。",
        TaskType.RECOMMENDATION: "从第一项推荐开始执行，完成后再决定下一步。",
        TaskType.REVIEW: "先复盘最近一次错误，再继续做新的题目。",
        TaskType.PROFILE: "先查看画像变化，再用它指导后续练习方向。",
        TaskType.TRAINING_PLAN: "先执行第一项计划任务，然后再根据结果调整节奏。",
    }
    return mapping.get(task_type, "按当前建议继续推进。")


def _has_core_context(request_context: RequestContext) -> bool:
    return any(
        [
            request_context.question_title,
            request_context.question_content,
            request_context.user_code,
            request_context.judge_result,
        ]
    )


def _read_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return value.strip() if isinstance(value, str) else ""


def _first_line(text: str) -> str:
    return text.splitlines()[0].strip() if text else ""


def _read_confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    return 0.75


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        parts = [_coerce_text(item) for item in value]
        return "、".join(part for part in parts if part)
    if isinstance(value, dict):
        return _coerce_text(value.get("text") or value.get("summary") or value.get("value"))
    return str(value).strip()
