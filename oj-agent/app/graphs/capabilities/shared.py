from dataclasses import dataclass
from typing import Iterable

from app.guardrails.runtime import GuardrailInput, GuardrailOutput, GuardrailRuntime
from app.retrieval.models import RetrievalQuery, RetrievalResult
from app.retrieval.runtime import RetrievalRuntime
from app.runtime.enums import RiskLevel, RunStatus
from app.runtime.models import EvidenceItem, EvidenceState, GuardrailState


@dataclass(frozen=True)
class CapabilitySupport:
    retrieval: RetrievalResult
    request_guard: GuardrailOutput
    evidence_guard: GuardrailOutput


def collect_capability_support(request, *, query_fields: Iterable[str]) -> CapabilitySupport:
    retrieval = RetrievalRuntime().retrieve(
        RetrievalQuery(
            query_text=" ".join(
                value
                for field_name in query_fields
                for value in [getattr(request, field_name, None)]
                if value
            ),
            task_type=request.task_type.value,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
        )
    )
    guardrail_runtime = GuardrailRuntime()
    request_guard = guardrail_runtime.evaluate(
        GuardrailInput(
            task_type=request.task_type.value,
            user_message=request.user_message,
            question_title=request.question_title,
            question_content=request.question_content,
            user_code=request.user_code,
            judge_result=request.judge_result,
        )
    )
    evidence_guard = guardrail_runtime.evaluate_evidence(
        task_type=request.task_type.value,
        evidence_count=len(retrieval.items),
        route_names=retrieval.route_names,
    )
    return CapabilitySupport(
        retrieval=retrieval,
        request_guard=request_guard,
        evidence_guard=evidence_guard,
    )


def build_evidence_state(retrieval: RetrievalResult) -> EvidenceState:
    return EvidenceState(
        items=[
            EvidenceItem(
                evidence_id=item.evidence_id,
                source_type=item.source_type,
                source_id=item.source_id,
                title=item.title,
                snippet=item.snippet,
                recall_score=item.score,
                metadata={"route_name": item.route_name, **item.metadata},
            )
            for item in retrieval.items
        ],
        route_names=retrieval.route_names,
        coverage_score=1.0 if retrieval.items else 0.0,
    )


def build_guardrail_state(request_guard: GuardrailOutput, evidence_guard: GuardrailOutput) -> GuardrailState:
    return GuardrailState(
        risk_level=_higher_risk(request_guard.risk_level, evidence_guard.risk_level),
        completeness_ok=request_guard.completeness_ok and evidence_guard.completeness_ok,
        policy_ok=request_guard.policy_ok and evidence_guard.policy_ok,
        dirty_data_flags=request_guard.missing_fields + evidence_guard.missing_fields,
        risk_reasons=request_guard.risk_reasons + evidence_guard.risk_reasons,
    )


def update_execution(execution, *, active_node: str, status: RunStatus = RunStatus.SUCCEEDED):
    return execution.model_copy(
        update={
            "status": status,
            "active_node": active_node,
        }
    )


def _higher_risk(left: RiskLevel, right: RiskLevel) -> RiskLevel:
    order = {
        RiskLevel.LOW: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.HIGH: 3,
    }
    return left if order[left] >= order[right] else right
