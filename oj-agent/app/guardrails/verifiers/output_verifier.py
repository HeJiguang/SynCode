from app.guardrails.runtime import GuardrailOutput
from app.runtime.enums import RiskLevel


class OutputVerifier:
    verifier_name = "output_verifier"

    def verify(self, *, answer: str, evidence_count: int) -> GuardrailOutput:
        normalized_answer = answer.lower()
        direct_code_leak = "full ac code" in normalized_answer or "submit directly" in normalized_answer
        unsupported_answer = evidence_count <= 0 and bool(answer.strip())

        risk_level = RiskLevel.LOW
        policy_ok = True
        risk_reasons: list[str] = []

        if direct_code_leak:
            risk_level = RiskLevel.HIGH
            policy_ok = False
            risk_reasons.append("direct solution leakage")
        elif unsupported_answer:
            risk_level = RiskLevel.MEDIUM
            risk_reasons.append("answer lacks evidence support")

        return GuardrailOutput(
            risk_level=risk_level,
            completeness_ok=True,
            policy_ok=policy_ok,
            missing_fields=[],
            risk_reasons=risk_reasons,
            triggered_verifiers=[self.verifier_name],
        )
