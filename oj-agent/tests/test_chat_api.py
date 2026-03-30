from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.main import app  # noqa: E402
from app.runtime.enums import RiskLevel, RunStatus, TaskType  # noqa: E402
from app.runtime.models import (  # noqa: E402
    EvidenceState,
    ExecutionState,
    GuardrailState,
    OutcomeState,
    RequestContext,
    UnifiedAgentState,
)
from app.services.conversation_memory import conversation_memory_store  # noqa: E402


client = TestClient(app)


def setup_function():
    conversation_memory_store.clear()


@pytest.fixture(autouse=True)
def clear_llm_env(monkeypatch):
    monkeypatch.delenv("OJ_AGENT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OJ_AGENT_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("OJ_AGENT_CHAT_MODEL", raising=False)
    monkeypatch.delenv("OJ_AGENT_TRAINING_MODEL", raising=False)
    monkeypatch.delenv("OJ_AGENT_LLM_PROVIDER", raising=False)


def test_chat_stream_emits_intent_specific_status_before_final_event():
    response = client.post(
        "/api/chat/stream",
        json={
            "trace_id": "trace-001",
            "user_id": "u-1",
            "question_title": "Two Sum",
            "judge_result": "WA on sample #2",
            "user_code": "public class Solution {}",
            "user_message": "Help me look.",
        },
    )

    assert response.status_code == 200
    assert "event: status" in response.text
    assert '"node":"context_analyzer"' in response.text
    assert '"node":"router"' in response.text
    assert '"node":"failure_diagnoser"' in response.text
    assert '"node":"finalizer"' in response.text
    assert "event: final" in response.text


def test_chat_returns_recommendation_guidance_for_practice_request():
    response = client.post(
        "/api/chat",
        json={
            "trace_id": "trace-002",
            "user_id": "u-1",
            "question_title": "Two Sum",
            "question_content": "Find two numbers that add up to target.",
            "user_message": "What should I practice next after this problem?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "recommend_question"
    assert "Practice plan:" in payload["answer"]
    assert payload["confidence"] >= 0.7
    assert payload["next_action"]


def test_chat_returns_confidence_and_next_action_for_failure_analysis():
    response = client.post(
        "/api/chat",
        json={
            "trace_id": "trace-003",
            "user_id": "u-1",
            "question_title": "Two Sum",
            "judge_result": "WA on sample #2",
            "user_code": "public class Solution {}",
            "user_message": "Why is this WA?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "analyze_failure"
    assert payload["confidence"] >= 0.8
    assert payload["next_action"]


def test_chat_reuses_conversation_context_for_follow_up_request():
    first_response = client.post(
        "/api/chat",
        json={
            "trace_id": "trace-004",
            "user_id": "u-1",
            "conversation_id": "conv-1",
            "question_id": "1001",
            "question_title": "Two Sum",
            "question_content": "Find two numbers that add up to target.",
            "judge_result": "WA on sample #2",
            "user_code": "public class Solution {}",
            "user_message": "Why is this WA?",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["intent"] == "analyze_failure"

    follow_up_response = client.post(
        "/api/chat",
        json={
            "trace_id": "trace-005",
            "user_id": "u-1",
            "conversation_id": "conv-1",
            "user_message": "Can you go deeper on that?",
        },
    )

    assert follow_up_response.status_code == 200
    payload = follow_up_response.json()
    assert payload["intent"] == "analyze_failure"
    assert "Question: Two Sum" in payload["answer"]
    assert payload["confidence"] >= 0.8


def test_chat_accepts_gateway_headers_and_camel_case_payload(monkeypatch):
    response = client.post(
        "/api/chat",
        headers={
            "X-User-Id": "u-9",
        },
        json={
            "questionTitle": "Two Sum",
            "questionContent": "Find two numbers that add up to target.",
            "userCode": "class Solution {}",
            "judgeResult": "WA on sample #2",
            "userMessage": "Why is this still wrong?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "analyze_failure"
    assert "Diagnosis summary:" in payload["answer"]
    assert "Question: Two Sum" in payload["answer"]
    assert payload["confidence"] >= 0.8
    assert payload["next_action"]


def test_chat_routes_review_requests_to_phase2_review_graph():
    response = client.post(
        "/api/chat",
        json={
            "trace_id": "trace-006",
            "user_id": "u-1",
            "user_message": "Summarize my recent practice and mistakes.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "review_summary"
    assert "Review summary:" in payload["answer"]
    assert payload["next_action"]


def test_chat_routes_profile_requests_to_phase2_profile_graph():
    response = client.post(
        "/api/chat",
        json={
            "trace_id": "trace-007",
            "user_id": "u-1",
            "user_message": "Update my learning profile based on recent submissions.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "profile_update"
    assert "Profile update summary:" in payload["answer"]
    assert payload["next_action"]


def test_chat_sync_uses_runtime_engine(monkeypatch):
    import app.api.chat as chat_module  # noqa: WPS433

    monkeypatch.setattr(
        chat_module,
        "execute_chat_request",
        lambda request, headers: UnifiedAgentState(
            request=RequestContext(
                trace_id="trace-runtime-sync",
                user_id="u-9",
                task_type=TaskType.CHAT,
                user_message=request.user_message,
            ),
            execution=ExecutionState(
                run_id="run-runtime-sync",
                graph_name="supervisor_graph",
                status=RunStatus.SUCCEEDED,
                active_node="chat_capability",
            ),
            evidence=EvidenceState(),
            guardrail=GuardrailState(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
            ),
            outcome=OutcomeState(
                intent="analyze_failure",
                answer="Runtime answer",
                confidence=0.95,
                next_action="Runtime next action",
            ),
        ),
        raising=False,
    )

    response = client.post(
        "/api/chat",
        headers={
            "X-User-Id": "u-9",
        },
        json={
            "questionTitle": "Two Sum",
            "userMessage": "Why is this still wrong?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Runtime answer"
    assert payload["intent"] == "analyze_failure"
    assert payload["confidence"] == 0.95
    assert payload["next_action"] == "Runtime next action"


def test_chat_detail_returns_same_shape_as_chat(monkeypatch):
    from app.services import chat_assistant  # noqa: WPS433

    monkeypatch.setattr(
        chat_assistant,
        "generate_chat_answer",
        lambda state: (
            "Detailed answer",
            0.93,
            "Trace the smallest failing sample.",
            "mock-detail-model",
        ),
    )

    response = client.post(
        "/api/chat/detail",
        headers={
            "X-User-Id": "u-9",
        },
        json={
            "questionTitle": "Two Sum",
            "userMessage": "Explain this failure in more detail.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Detailed answer"
    assert payload["confidence"] == 0.93
    assert payload["next_action"] == "Trace the smallest failing sample."


def test_chat_stream_emits_delta_events_for_incremental_llm_output(monkeypatch):
    from app.services import chat_assistant  # noqa: WPS433

    monkeypatch.setattr(
        chat_assistant,
        "stream_chat_answer",
        lambda state: iter(["Hel", "lo"]),
    )
    monkeypatch.setattr(
        chat_assistant,
        "generate_chat_answer",
        lambda state: (
            "Hello",
            0.87,
            "Ask for one more concrete failing example.",
            "mock-stream-model",
        ),
    )

    response = client.post(
        "/api/chat/stream",
        headers={
            "X-User-Id": "u-3",
        },
        json={
            "questionTitle": "Two Sum",
            "judgeResult": "WA on sample #2",
            "userCode": "class Solution {}",
            "userMessage": "Help me look.",
        },
    )

    assert response.status_code == 200
    assert "event: delta" in response.text
    assert '"answer":"Hel"' in response.text
    assert '"answer":"Hello"' in response.text
    assert "event: final" in response.text


def test_chat_stream_uses_runtime_streaming(monkeypatch):
    import app.api.chat as chat_module  # noqa: WPS433

    monkeypatch.setattr(
        chat_module,
        "stream_chat_request",
        lambda request, headers: iter(
            [
                'event: final\ndata: {"answer":"Runtime stream answer","confidence":0.81,"next_action":"Keep tracing the failing sample."}\n\n'
            ]
        ),
    )

    response = client.post(
        "/api/chat/stream",
        json={
            "questionTitle": "Two Sum",
            "userMessage": "Help me look.",
        },
    )

    assert response.status_code == 200
    assert "Runtime stream answer" in response.text
