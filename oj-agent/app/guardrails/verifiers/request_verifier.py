from app.guardrails.runtime import GuardrailInput, GuardrailOutput
from app.runtime.enums import RiskLevel


class RequestVerifier:
    verifier_name = "request_verifier"

    def verify(self, guardrail_input: GuardrailInput) -> GuardrailOutput:
        missing_fields: list[str] = []
        if not guardrail_input.question_title and not guardrail_input.question_content:
            missing_fields.append("question statement")
        if not guardrail_input.user_code:
            missing_fields.append("code")
        if not guardrail_input.judge_result:
            missing_fields.append("judge result")

        return GuardrailOutput(
            risk_level=RiskLevel.MEDIUM if missing_fields else RiskLevel.LOW,
            completeness_ok=not missing_fields,
            policy_ok=True,
            missing_fields=missing_fields,
            risk_reasons=["missing critical context"] if missing_fields else [],
            triggered_verifiers=[self.verifier_name],
        )
