from pydantic import BaseModel, Field

from app.runtime.enums import RiskLevel


class GuardrailInput(BaseModel):
    task_type: str
    user_message: str
    question_title: str | None = None
    question_content: str | None = None
    user_code: str | None = None
    judge_result: str | None = None


class GuardrailOutput(BaseModel):
    risk_level: RiskLevel
    completeness_ok: bool
    policy_ok: bool
    missing_fields: list[str] = Field(default_factory=list)
    risk_reasons: list[str] = Field(default_factory=list)
    triggered_verifiers: list[str] = Field(default_factory=list)


class GuardrailRuntime:
    def __init__(self) -> None:
        from app.guardrails.verifiers import EvidenceVerifier, OutputVerifier, RequestVerifier

        self.request_verifiers = [RequestVerifier()]
        self.evidence_verifiers = [EvidenceVerifier()]
        self.output_verifiers = [OutputVerifier()]

    def _merge_outputs(self, outputs: list[GuardrailOutput]) -> GuardrailOutput:
        highest_risk = RiskLevel.LOW
        for output in outputs:
            if output.risk_level is RiskLevel.HIGH:
                highest_risk = RiskLevel.HIGH
                break
            if output.risk_level is RiskLevel.MEDIUM:
                highest_risk = RiskLevel.MEDIUM

        missing_fields: list[str] = []
        risk_reasons: list[str] = []
        triggered_verifiers: list[str] = []
        policy_ok = True
        completeness_ok = True
        for output in outputs:
            missing_fields.extend(output.missing_fields)
            risk_reasons.extend(output.risk_reasons)
            triggered_verifiers.extend(output.triggered_verifiers)
            policy_ok = policy_ok and output.policy_ok
            completeness_ok = completeness_ok and output.completeness_ok

        return GuardrailOutput(
            risk_level=highest_risk,
            completeness_ok=completeness_ok,
            policy_ok=policy_ok,
            missing_fields=missing_fields,
            risk_reasons=risk_reasons,
            triggered_verifiers=triggered_verifiers,
        )

    def evaluate(self, guardrail_input: GuardrailInput) -> GuardrailOutput:
        outputs = [verifier.verify(guardrail_input) for verifier in self.request_verifiers]
        return self._merge_outputs(outputs)

    def evaluate_output(self, *, answer: str, evidence_count: int) -> GuardrailOutput:
        outputs = [
            verifier.verify(
                answer=answer,
                evidence_count=evidence_count,
            )
            for verifier in self.output_verifiers
        ]
        return self._merge_outputs(outputs)

    def evaluate_evidence(
        self,
        *,
        task_type: str,
        evidence_count: int,
        route_names: list[str] | None = None,
    ) -> GuardrailOutput:
        outputs = [
            verifier.verify(
                task_type=task_type,
                evidence_count=evidence_count,
                route_names=route_names,
            )
            for verifier in self.evidence_verifiers
        ]
        return self._merge_outputs(outputs)
