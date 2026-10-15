from app.agent_runtime.base import AgentRunResult
from app.schemas.training_plan_request import QuestionCandidate, TrainingPlanRequest
from app.services.training_planner import build_training_plan


def test_training_plan_filters_unknown_questions(monkeypatch):
    class Runtime:
        def generate_json(self, request):
            assert request.conversation_id == "training-user-1"
            return (
                AgentRunResult(
                    text="{}",
                    runtime_name="hermes",
                    provider="deepseek",
                    model_name="deepseek-chat",
                ),
                {
                    "current_level": ["starter"],
                    "target_direction": "algorithm_foundation",
                    "weak_points": ["hash table", "边界处理"],
                    "strong_points": "循环",
                    "plan_title": "哈希表训练",
                    "plan_goal": "稳定基础",
                    "ai_summary": "先练题，再复盘。",
                    "tasks": [
                        {"task_type": "question", "question_id": 999, "title_snapshot": "不存在"},
                        {
                            "task_type": "question",
                            "question_id": 101,
                            "title_snapshot": "Two Sum",
                            "task_order": 1,
                            "knowledge_tags_snapshot": ["array", "hash table"],
                        },
                    ],
                },
            )

    import app.services.training_planner as planner

    monkeypatch.setattr(planner, "build_agent_runtime", lambda: Runtime())
    response = build_training_plan(
        TrainingPlanRequest(
            trace_id="trace-1",
            user_id=1,
            conversation_id="training-user-1",
            candidate_questions=[QuestionCandidate(question_id=101, title="Two Sum")],
        )
    )

    assert [task.question_id for task in response.tasks] == [101]
    assert response.weak_points == "hash table、边界处理"
    assert response.tasks[0].knowledge_tags_snapshot == "array、hash table"
