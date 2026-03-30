from app.guardrails.runtime import GuardrailOutput
from app.runtime.enums import RiskLevel


class EvidenceVerifier:
    verifier_name = "evidence_verifier"

    def verify(
        self,
        *,
        task_type: str,
        evidence_count: int,
        route_names: list[str] | None = None,
    ) -> GuardrailOutput:
        route_names = route_names or []
        if evidence_count > 0:
            needs_diversity = task_type in {"review", "profile", "training_plan"}
            if needs_diversity and len(route_names) < 2:
                return GuardrailOutput(
                    risk_level=RiskLevel.MEDIUM,
                    completeness_ok=False,
                    policy_ok=True,
                    missing_fields=[],
                    risk_reasons=["evidence diversity is insufficient"],
                    triggered_verifiers=[self.verifier_name],
                )
            return GuardrailOutput(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=[],
                triggered_verifiers=[self.verifier_name],
            )

        if task_type in {"diagnosis", "recommendation", "review", "profile", "training_plan"}:
            return GuardrailOutput(
                risk_level=RiskLevel.MEDIUM,
                completeness_ok=False,
                policy_ok=True,
                missing_fields=[],
                risk_reasons=["evidence coverage is insufficient"],
                triggered_verifiers=[self.verifier_name],
            )

        return GuardrailOutput(
            risk_level=RiskLevel.LOW,
            completeness_ok=True,
            policy_ok=True,
            missing_fields=[],
            risk_reasons=[],
            triggered_verifiers=[self.verifier_name],
        )
