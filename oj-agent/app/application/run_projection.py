from collections.abc import Callable, Mapping

from app.domain.artifacts import Artifact, ArtifactType, RenderHint
from app.domain.runs import EventType
from app.domain.write_intents import (
    RiskLevel as WriteRiskLevel,
    TargetService,
    UserImpactLevel,
    WriteIntent as StoredWriteIntent,
    WriteIntentType,
)
from app.runtime.enums import RiskLevel
from app.runtime.models import UnifiedAgentState, WriteIntent


def build_runtime_artifact(run_id: str, state: UnifiedAgentState) -> Artifact:
    artifact_type, render_hint, title = _artifact_profile_for_intent(state.outcome.intent)
    answer = (state.outcome.answer or "").strip()
    next_action = (state.outcome.next_action or "").strip()
    response_payload = dict(state.outcome.response_payload)

    return Artifact(
        run_id=run_id,
        artifact_type=artifact_type,
        title=title,
        summary=_summary_for_state(answer, next_action, response_payload),
        body={
            "intent": state.outcome.intent,
            "answer": answer,
            "nextAction": next_action,
            "confidence": state.outcome.confidence,
            "riskLevel": state.guardrail.risk_level.value,
            "questionTitle": state.request.question_title,
            "statusEvents": list(state.outcome.status_events),
            "responsePayload": response_payload,
        },
        render_hint=render_hint,
    )


def build_failure_artifact(run_id: str, *, message: str) -> Artifact:
    return Artifact(
        run_id=run_id,
        artifact_type=ArtifactType.ANSWER_CARD,
        title="Run failed",
        summary="The runtime could not finish this request.",
        body={
            "intent": "run_failed",
            "answer": message,
            "nextAction": "Retry the request after checking the latest workspace context.",
        },
        render_hint=RenderHint.TIMELINE_CARD,
    )


def project_runtime_events(
    run_id: str,
    state: UnifiedAgentState,
    *,
    append_event: Callable[[str, EventType, dict | None], object],
) -> None:
    if state.evidence.route_names:
        append_event(
            run_id,
            EventType.RETRIEVAL_EVIDENCE_READY,
            {
                "graphName": state.execution.graph_name,
                "routeNames": list(state.evidence.route_names),
                "evidenceCount": len(state.evidence.items),
            },
        )

    if (
        state.guardrail.risk_level is not RiskLevel.LOW
        or not state.guardrail.completeness_ok
        or not state.guardrail.policy_ok
    ):
        append_event(
            run_id,
            EventType.GUARDRAIL_TRIGGERED,
            {
                "riskLevel": state.guardrail.risk_level.value,
                "completenessOk": state.guardrail.completeness_ok,
                "policyOk": state.guardrail.policy_ok,
                "riskReasons": list(state.guardrail.risk_reasons),
            },
        )

    for status_event in state.outcome.status_events:
        payload = dict(status_event)
        node_name = str(payload.get("node") or "unknown")
        append_event(
            run_id,
            EventType.GRAPH_NODE_COMPLETED,
            {
                "node": node_name,
                "graphName": state.execution.graph_name,
                **payload,
            },
        )


def register_runtime_write_intents(
    run_id: str,
    user_id: str,
    state: UnifiedAgentState,
    *,
    register_write_intent: Callable[[StoredWriteIntent], tuple[object, object]],
) -> None:
    for runtime_write_intent in state.outcome.write_intents:
        register_write_intent(
            _to_stored_write_intent(
                run_id=run_id,
                user_id=user_id,
                runtime_write_intent=runtime_write_intent,
                runtime_risk=state.guardrail.risk_level,
            )
        )


def _artifact_profile_for_intent(intent: str | None) -> tuple[ArtifactType, RenderHint, str]:
    profiles: Mapping[str, tuple[ArtifactType, RenderHint, str]] = {
        "analyze_failure": (ArtifactType.DIAGNOSIS_REPORT, RenderHint.DIAGNOSIS, "Diagnosis summary"),
        "recommend_question": (ArtifactType.RECOMMENDATION_PACK, RenderHint.RECOMMENDATION, "Practice recommendation"),
        "review_summary": (ArtifactType.REVIEW_SUMMARY, RenderHint.MARKDOWN, "Practice review"),
        "profile_update": (ArtifactType.PROFILE_DELTA, RenderHint.PROFILE_DELTA, "Profile update"),
        "training_plan": (ArtifactType.TRAINING_PLAN, RenderHint.PLAN, "Training plan"),
    }
    return profiles.get(intent or "", (ArtifactType.ANSWER_CARD, RenderHint.MARKDOWN, "Assistant answer"))


def _summary_for_state(answer: str, next_action: str, response_payload: dict[str, object]) -> str:
    plan_title = response_payload.get("plan_title")
    if isinstance(plan_title, str) and plan_title.strip():
        return plan_title.strip()[:180]
    if answer:
        first_line = answer.splitlines()[0].strip()
        return first_line[:180]
    if next_action:
        return next_action[:180]
    return "The runtime completed without a detailed summary."


def _to_stored_write_intent(
    *,
    run_id: str,
    user_id: str,
    runtime_write_intent: WriteIntent,
    runtime_risk: RiskLevel,
) -> StoredWriteIntent:
    intent_type = _map_intent_type(runtime_write_intent.intent_type)
    return StoredWriteIntent(
        run_id=run_id,
        user_id=user_id,
        intent_type=intent_type,
        target_service=_map_target_service(runtime_write_intent.target_service),
        target_aggregate=_target_aggregate_for_intent(intent_type),
        payload=dict(runtime_write_intent.payload),
        risk_level=_map_risk_level(runtime_risk),
        user_impact_level=_impact_level_for_intent(intent_type),
    )


def _map_intent_type(intent_type: str) -> WriteIntentType:
    mapping = {
        "profile_update_write": WriteIntentType.PROFILE_UPDATE,
        "training_plan_write": WriteIntentType.TRAINING_PLAN_RECOMPUTE,
        "message_delivery_write": WriteIntentType.MESSAGE_DELIVERY,
        "review_snapshot_write": WriteIntentType.REVIEW_SNAPSHOT_WRITE,
        "weakness_tag_update_write": WriteIntentType.WEAKNESS_TAG_UPDATE,
    }
    try:
        return mapping[intent_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported runtime write intent: {intent_type}") from exc


def _map_target_service(target_service: str) -> TargetService:
    if target_service == TargetService.OJ_SYSTEM.value:
        return TargetService.OJ_SYSTEM
    return TargetService.OJ_FRIEND


def _target_aggregate_for_intent(intent_type: WriteIntentType) -> str:
    mapping = {
        WriteIntentType.PROFILE_UPDATE: "learning_profile",
        WriteIntentType.WEAKNESS_TAG_UPDATE: "weakness_tags",
        WriteIntentType.TRAINING_PLAN_RECOMPUTE: "training_plan",
        WriteIntentType.TRAINING_PLAN_REPLACE: "training_plan",
        WriteIntentType.MESSAGE_DELIVERY: "inbox_message",
        WriteIntentType.REVIEW_SNAPSHOT_WRITE: "review_snapshot",
    }
    return mapping[intent_type]


def _impact_level_for_intent(intent_type: WriteIntentType) -> UserImpactLevel:
    if intent_type is WriteIntentType.TRAINING_PLAN_REPLACE:
        return UserImpactLevel.HIGH
    if intent_type in {WriteIntentType.TRAINING_PLAN_RECOMPUTE, WriteIntentType.WEAKNESS_TAG_UPDATE}:
        return UserImpactLevel.MEDIUM
    return UserImpactLevel.LOW


def _map_risk_level(risk_level: RiskLevel) -> WriteRiskLevel:
    mapping = {
        RiskLevel.LOW: WriteRiskLevel.LOW,
        RiskLevel.MEDIUM: WriteRiskLevel.MEDIUM,
        RiskLevel.HIGH: WriteRiskLevel.HIGH,
    }
    return mapping[risk_level]
