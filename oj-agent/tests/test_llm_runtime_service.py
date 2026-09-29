from app.agent_runtime import AgentRunResult
from app.runtime.enums import TaskType
from app.runtime.models import RequestContext
from app.schemas.training_plan_request import QuestionCandidate, TrainingPlanRequest
from app.services.llm_runtime_service import (
    _normalize_training_plan_payload,
    _normalize_tutor_metadata,
    execute_chat_with_llm,
)


def test_chat_runtime_receives_stable_conversation_context(monkeypatch):
    captured = []

    class FakeRuntime:
        def generate_json(self, request):
            captured.append(request)
            return (
                AgentRunResult(
                    text='{"answer":"先检查空数组。"}',
                    runtime_name="hermes",
                    provider="deepseek",
                    model_name="deepseek-v4-pro",
                    session_id="session-1",
                    remote_run_id="run-1",
                ),
                {
                    "intent": "explain_problem",
                    "title": "解题提示",
                    "summary": "检查边界条件",
                    "answer": "先检查空数组。",
                    "next_action": "补充空数组测试。",
                    "confidence": 0.9,
                },
            )

    import app.services.llm_runtime_service as service_module  # noqa: WPS433

    monkeypatch.setattr(service_module, "build_agent_runtime", lambda: FakeRuntime())

    state = execute_chat_with_llm(
        RequestContext(
            trace_id="trace-chat-1",
            user_id="user-7",
            task_type=TaskType.CHAT,
            user_message="给我一个提示",
            conversation_id="syncode-question-42",
            question_id="42",
            question_title="Two Sum",
        )
    )

    assert captured[0].conversation_id == "syncode-question-42"
    assert captured[0].user_id == "user-7"
    assert state.execution.model_name == "deepseek-v4-pro"
    assert state.evidence.route_names == ["agent_runtime", "hermes"]
    assert state.outcome.answer == "先检查空数组。"


def test_normalize_training_plan_payload_coerces_scalar_summary_fields():
    request = TrainingPlanRequest(
        trace_id="trace-training-normalize-001",
        user_id=1,
        current_level="starter",
        target_direction="algorithm_foundation",
        candidate_questions=[
            QuestionCandidate(
                question_id=101,
                title="Two Sum",
                difficulty=1,
                algorithm_tag="array",
                knowledge_tags="hash table",
                estimated_minutes=15,
            )
        ],
    )

    response = _normalize_training_plan_payload(
        request,
        {
            "current_level": ["starter"],
            "target_direction": ["algorithm_foundation"],
            "weak_points": ["hash table", "边界处理"],
            "strong_points": ["数学基础"],
            "plan_title": ["两数之和训练计划"],
            "plan_goal": ["夯实哈希表基础"],
            "ai_summary": ["先练题，再复盘。"],
            "tasks": [
                {
                    "task_type": "question",
                    "question_id": 101,
                    "title_snapshot": "Two Sum",
                    "task_order": 1,
                    "recommended_reason": "Strengthen hash map basics.",
                    "knowledge_tags_snapshot": ["hash table", "array"],
                }
            ],
        },
    )

    assert response.current_level == "starter"
    assert response.target_direction == "algorithm_foundation"
    assert response.weak_points == "hash table、边界处理"
    assert response.strong_points == "数学基础"
    assert response.plan_title == "两数之和训练计划"
    assert response.plan_goal == "夯实哈希表基础"
    assert response.ai_summary == "先练题，再复盘。"
    assert response.tasks[0].knowledge_tags_snapshot == "hash table、array"


def test_normalize_tutor_metadata_tolerates_non_numeric_hint_level():
    metadata = _normalize_tutor_metadata(
        {
            "hint_level": "give-a-small-hint",
            "memory_candidates": [{"content": "用户偏好先看提示。", "confidence": 0.9}],
        }
    )

    assert metadata["hint_level"] == 1
    assert metadata["memory_candidates"][0]["content"] == "用户偏好先看提示。"
