from app.schemas.training_plan_request import QuestionCandidate, TrainingPlanRequest
from app.services.llm_runtime_service import _normalize_training_plan_payload


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
