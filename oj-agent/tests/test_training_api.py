from fastapi.testclient import TestClient

from app.main import app
from app.schemas.training_plan_response import TrainingPlanResponse


client = TestClient(app)


def test_training_api_returns_generated_plan(monkeypatch):
    import app.api.training as training_module

    monkeypatch.setattr(
        training_module,
        "build_training_plan",
        lambda _request: TrainingPlanResponse.model_validate(
            {
                "current_level": "starter",
                "target_direction": "algorithm_foundation",
                "weak_points": "hash table",
                "strong_points": "array iteration",
                "plan_title": "基础训练计划",
                "plan_goal": "巩固哈希表基础",
                "ai_summary": "先练习，再复盘。",
                "tasks": [
                    {
                        "task_type": "question",
                        "question_id": 101,
                        "title_snapshot": "Two Sum",
                        "task_order": 1,
                    }
                ],
            }
        ),
    )

    response = client.post(
        "/api/training/plan",
        json={
            "trace_id": "trace-1",
            "user_id": 1,
            "user_request": "补强哈希表基础",
            "candidate_questions": [{"question_id": 101, "title": "Two Sum"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["tasks"][0]["question_id"] == 101


def test_training_api_reports_unavailable_runtime(monkeypatch):
    import app.api.training as training_module

    def fail(_request):
        raise RuntimeError("未配置可用的大模型。")

    monkeypatch.setattr(training_module, "build_training_plan", fail)
    response = client.post(
        "/api/training/plan",
        json={"trace_id": "trace-2", "user_id": 1, "user_request": "安排基础训练"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "未配置可用的大模型。"


def test_training_api_rejects_blank_user_request():
    response = client.post(
        "/api/training/plan",
        json={"trace_id": "trace-3", "user_id": 1, "user_request": "   "},
    )

    assert response.status_code == 422
