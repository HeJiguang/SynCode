from app.guardrails.runtime import GuardrailInput, GuardrailRuntime
from app.runtime.enums import RiskLevel


def test_guardrail_runtime_marks_missing_context_as_medium_risk():
    runtime = GuardrailRuntime()

    result = runtime.evaluate(
        GuardrailInput(
            task_type="chat",
            user_message="Help me look.",
            question_title=None,
            question_content=None,
            user_code=None,
            judge_result=None,
        )
    )

    assert result.risk_level is RiskLevel.MEDIUM
    assert result.completeness_ok is False
    assert "question statement" in result.missing_fields
    assert "code" in result.missing_fields
    assert "judge result" in result.missing_fields


def test_guardrail_runtime_blocks_direct_ac_code_policy():
    runtime = GuardrailRuntime()

    result = runtime.evaluate_output(
        answer="Here is the full AC code you can submit directly.",
        evidence_count=2,
    )

    assert result.policy_ok is False
    assert result.risk_level is RiskLevel.HIGH
    assert result.risk_reasons


def test_guardrail_runtime_collects_triggered_verifiers():
    runtime = GuardrailRuntime()

    result = runtime.evaluate(
        GuardrailInput(
            task_type="diagnosis",
            user_message="Why is this WA?",
            question_title="Two Sum",
            question_content=None,
            user_code=None,
            judge_result="WA on sample #2",
        )
    )

    assert hasattr(result, "triggered_verifiers")
    assert result.triggered_verifiers


def test_guardrail_runtime_flags_missing_evidence_for_diagnosis():
    runtime = GuardrailRuntime()

    result = runtime.evaluate_evidence(
        task_type="diagnosis",
        evidence_count=0,
    )

    assert result.risk_level is RiskLevel.MEDIUM
    assert "evidence_verifier" in result.triggered_verifiers


def test_guardrail_runtime_flags_low_route_diversity_for_review():
    runtime = GuardrailRuntime()

    result = runtime.evaluate_evidence(
        task_type="review",
        evidence_count=1,
        route_names=["lexical"],
    )

    assert result.risk_level is RiskLevel.MEDIUM
    assert result.completeness_ok is False
    assert "evidence diversity is insufficient" in result.risk_reasons
