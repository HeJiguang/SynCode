from collections.abc import Mapping


_ARTIFACT_TYPE_LABELS = {
    "answer_card": "结果卡片",
    "diagnosis_report": "诊断报告",
    "recommendation_pack": "练习建议",
    "training_plan": "训练计划",
    "review_summary": "复盘总结",
    "profile_delta": "画像更新",
    "weakness_snapshot": "薄弱点快照",
    "message_pack": "消息卡片",
    "run_summary": "运行摘要",
}

_RENDER_HINT_LABELS = {
    "markdown": "富文本卡片",
    "diagnosis": "诊断卡片",
    "plan": "计划卡片",
    "profile_delta": "画像更新卡片",
    "recommendation": "推荐卡片",
    "timeline_card": "时间线卡片",
}

_RUN_STATUS_LABELS = {
    "ACCEPTED": "已创建",
    "QUEUED": "排队中",
    "RUNNING": "执行中",
    "WAITING_USER": "等待用户",
    "APPLYING": "应用中",
    "SUCCEEDED": "已完成",
    "PARTIALLY_APPLIED": "部分应用",
    "FAILED": "执行失败",
    "CANCELLED": "已取消",
}

_RUN_TYPE_LABELS = {
    "interactive_tutor": "提示问答",
    "interactive_diagnosis": "诊断分析",
    "interactive_recommendation": "练习推荐",
    "interactive_plan": "训练规划",
    "interactive_review": "复盘总结",
    "judge_followup": "判题跟进",
    "profile_refresh": "画像刷新",
    "plan_recompute": "计划重算",
    "weakness_tracking": "薄弱点跟踪",
    "message_delivery": "消息投递",
}

_RUN_SOURCE_LABELS = {
    "workspace_panel": "工作区面板",
    "training_center": "训练中心",
    "judge_event": "判题事件",
    "scheduler": "调度任务",
    "admin_trigger": "管理触发",
}

_EVENT_TYPE_LABELS = {
    "run.accepted": "运行已创建",
    "run.queued": "运行已入队",
    "run.started": "开始执行",
    "graph.node_started": "节点开始执行",
    "graph.node_completed": "节点已完成",
    "retrieval.query_planned": "检索计划已生成",
    "retrieval.evidence_ready": "检索证据已准备",
    "tool.called": "已调用工具",
    "tool.succeeded": "工具执行成功",
    "tool.failed": "工具执行失败",
    "guardrail.triggered": "触发安全校验",
    "artifact.created": "结果卡片已生成",
    "write.intent_created": "写入意图已生成",
    "write.applied": "写入已应用",
    "write.blocked": "写入已阻止",
    "draft.created": "草案已生成",
    "run.completed": "运行已完成",
    "run.failed": "运行失败",
}

_INTENT_LABELS = {
    "ask_for_context": "补充上下文",
    "explain_problem": "解题提示",
    "analyze_failure": "诊断分析",
    "recommend_question": "练习推荐",
    "review_summary": "复盘总结",
    "profile_update": "画像更新",
    "training_plan": "训练计划",
    "unsupported_task": "暂不支持",
    "run_failed": "运行失败",
}

_NODE_LABELS = {
    "llm_runtime": "大模型运行时",
    "llm_prepare": "上下文整理",
    "llm_inference": "模型推理",
    "response_packaging": "结果封装",
    "training_plan_llm": "训练计划生成",
    "runtime_execution": "运行时执行",
}


def label_for_artifact_type(value: object) -> str:
    raw = _normalize_value(value)
    return _ARTIFACT_TYPE_LABELS.get(raw, raw or "结果卡片")


def label_for_render_hint(value: object) -> str:
    raw = _normalize_value(value)
    return _RENDER_HINT_LABELS.get(raw, raw or "卡片")


def label_for_run_status(value: object) -> str:
    raw = _normalize_value(value)
    return _RUN_STATUS_LABELS.get(raw, raw or "未知状态")


def label_for_run_type(value: object) -> str:
    raw = _normalize_value(value)
    return _RUN_TYPE_LABELS.get(raw, raw or "运行任务")


def label_for_run_source(value: object) -> str:
    raw = _normalize_value(value)
    return _RUN_SOURCE_LABELS.get(raw, raw or "触发来源")


def label_for_event_type(value: object) -> str:
    raw = _normalize_value(value)
    return _EVENT_TYPE_LABELS.get(raw, raw or "运行事件")


def label_for_intent(value: object) -> str:
    raw = _normalize_value(value)
    return _INTENT_LABELS.get(raw, raw or "结果")


def label_for_node(value: object) -> str:
    raw = _normalize_value(value)
    return _NODE_LABELS.get(raw, raw or "节点")


def enrich_run_model(raw: Mapping[str, object]) -> dict[str, object]:
    data = dict(raw)
    if data.get("status") is not None:
        data["status_label"] = label_for_run_status(data.get("status"))
    if data.get("run_type") is not None:
        data["run_type_label"] = label_for_run_type(data.get("run_type"))
    if data.get("source") is not None:
        data["source_label"] = label_for_run_source(data.get("source"))
    if data.get("entry_graph") is not None:
        data["entry_graph_label"] = label_for_node(data.get("entry_graph"))
    if data.get("active_node") is not None:
        data["active_node_label"] = label_for_node(data.get("active_node"))
    return data


def enrich_artifact_model(raw: Mapping[str, object]) -> dict[str, object]:
    data = dict(raw)
    data["artifact_type_label"] = label_for_artifact_type(data.get("artifact_type"))
    data["render_hint_label"] = label_for_render_hint(data.get("render_hint"))
    body = dict(data.get("body") or {})
    intent = _normalize_value(body.get("intent"))
    if intent:
        body["intent_label"] = label_for_intent(intent)
    status_events = body.get("status_events")
    if isinstance(status_events, list):
        body["status_events"] = [_enrich_status_event(item) for item in status_events]
    data["body"] = body
    return data


def enrich_run_event_model(raw: Mapping[str, object]) -> dict[str, object]:
    data = dict(raw)
    event_type = _normalize_value(data.get("event_type"))
    data["event_type_label"] = label_for_event_type(event_type)
    payload = dict(data.get("payload") or {})
    data["payload"] = _enrich_event_payload(event_type, payload)
    return data


def _enrich_status_event(raw: object) -> object:
    if not isinstance(raw, Mapping):
        return raw
    event = dict(raw)
    node = _normalize_value(event.get("node"))
    message = _normalize_value(event.get("message"))
    if node:
        event["node_label"] = label_for_node(node)
    if message:
        event["message_label"] = message
    return event


def _enrich_event_payload(event_type: str, payload: dict[str, object]) -> dict[str, object]:
    node = _normalize_value(payload.get("node"))
    if node:
        payload["nodeLabel"] = label_for_node(node)

    active_node = _normalize_value(payload.get("activeNode"))
    if active_node:
        payload["activeNodeLabel"] = label_for_node(active_node)

    graph_name = _normalize_value(payload.get("graphName"))
    if graph_name:
        payload["graphNameLabel"] = label_for_node(graph_name)

    artifact_type = _normalize_value(payload.get("artifactType"))
    if artifact_type:
        payload["artifactTypeLabel"] = label_for_artifact_type(artifact_type)

    status = _normalize_value(payload.get("status"))
    if status:
        payload["statusLabel"] = label_for_run_status(status)

    message = _normalize_value(payload.get("message"))
    if message:
        payload["messageLabel"] = message
    elif event_type == "graph.node_completed" and node:
        payload["messageLabel"] = f"节点“{label_for_node(node)}”已完成。"
    elif event_type == "artifact.created" and artifact_type:
        payload["messageLabel"] = f"已生成“{label_for_artifact_type(artifact_type)}”。"

    return payload


def _normalize_value(value: object) -> str:
    if value is None:
        return ""
    raw = getattr(value, "value", value)
    return str(raw)
