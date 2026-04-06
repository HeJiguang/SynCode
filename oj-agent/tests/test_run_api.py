from pathlib import Path
import sys

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.application.run_service import run_service  # noqa: E402
from app.domain.inbox import InboxItemType  # noqa: E402
from app.domain.runs import RunSource, RunType  # noqa: E402
from app.domain.write_intents import (  # noqa: E402
    TargetService,
    UserImpactLevel,
    WriteIntent as StoredWriteIntent,
    WriteIntentType,
)
from app.main import app  # noqa: E402
from app.runtime.enums import RiskLevel, RunStatus, TaskType  # noqa: E402
from app.runtime.models import (  # noqa: E402
    EvidenceState,
    ExecutionState,
    GuardrailState,
    OutcomeState,
    RequestContext,
    UnifiedAgentState,
    WriteIntent,
)


client = TestClient(app)


def setup_function():
    run_service.clear()


def _fake_chat_state(trace_id: str, user_id: str, message: str, question_title: str | None, judge_result: str | None):
    return UnifiedAgentState(
        request=RequestContext(
            trace_id=trace_id,
            user_id=user_id,
            task_type=TaskType.CHAT,
            user_message=message,
            question_title=question_title,
            judge_result=judge_result,
        ),
        execution=ExecutionState(
            run_id=trace_id,
            graph_name="llm_runtime",
            status=RunStatus.SUCCEEDED,
            active_node="response_packaging",
            model_name="deepseek-chat",
        ),
        evidence=EvidenceState(route_names=["llm_only"]),
        guardrail=GuardrailState(
            risk_level=RiskLevel.LOW,
            completeness_ok=True,
            policy_ok=True,
        ),
        outcome=OutcomeState(
            intent="explain_problem",
            answer="先用哈希表记录已经出现过的数字。",
            confidence=0.92,
            next_action="先手推样例 [2,7,11,15]。",
            status_events=[
                {"node": "llm_prepare", "message": "已整理大模型输入上下文。"},
                {"node": "llm_inference", "message": "已完成推理。"},
                {"node": "response_packaging", "message": "已整理模型输出结果。"},
            ],
        ),
    )


def test_create_run_returns_camel_case_run_metadata_and_bootstrap_artifact(monkeypatch):
    import app.api.runs as runs_module  # noqa: WPS433

    monkeypatch.setattr(
        runs_module,
        "execute_run_request",
        lambda request, user_id, trace_id, headers: _fake_chat_state(
            trace_id,
            user_id,
            request.context.user_message or "",
            request.context.question_title,
            request.context.judge_result,
        ),
        raising=False,
    )

    response = client.post(
        "/api/runs",
        json={
            "runType": "interactive_tutor",
            "source": "workspace_panel",
            "userId": "u-1",
            "conversationId": "conv-1",
            "context": {
                "questionId": "1001",
                "questionTitle": "Two Sum",
                "judgeResult": "WA on sample #2",
                "userMessage": "Why is this still wrong?",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runId"]
    assert payload["status"] == "SUCCEEDED"
    assert payload["statusLabel"] == "已完成"
    assert payload["entryGraph"] == "llm_runtime"
    assert payload["entryGraphLabel"] == "大模型运行时"
    assert payload["bootstrapArtifactId"]

    run_snapshot = client.get(f"/api/runs/{payload['runId']}")
    assert run_snapshot.status_code == 200
    assert run_snapshot.json()["runId"] == payload["runId"]
    assert "contextRef" in run_snapshot.json()

    artifacts = client.get(f"/api/runs/{payload['runId']}/artifacts")
    assert artifacts.status_code == 200
    assert artifacts.json()[0]["artifactId"]
    assert artifacts.json()[0]["title"] == "智能体任务已创建"
    assert artifacts.json()[0]["artifactTypeLabel"] == "结果卡片"
    assert artifacts.json()[0]["renderHintLabel"] == "时间线卡片"


def test_run_events_endpoint_streams_camel_case_events(monkeypatch):
    import app.api.runs as runs_module  # noqa: WPS433

    monkeypatch.setattr(
        runs_module,
        "execute_run_request",
        lambda request, user_id, trace_id, headers: _fake_chat_state(
            trace_id,
            user_id,
            request.context.user_message or "",
            request.context.question_title,
            request.context.judge_result,
        ),
        raising=False,
    )

    response = client.post(
        "/api/runs",
        json={
            "runType": "interactive_diagnosis",
            "source": "workspace_panel",
            "userId": "u-2",
            "context": {
                "questionTitle": "Two Sum",
                "judgeResult": "WA on sample #2",
                "userMessage": "Help me diagnose this.",
            },
        },
    )
    run_id = response.json()["runId"]

    event_response = client.get(f"/api/runs/{run_id}/events")

    assert event_response.status_code == 200
    assert "event: run_event" in event_response.text
    assert '"eventType": "run.accepted"' in event_response.text
    assert '"eventType": "artifact.created"' in event_response.text


def test_create_run_projects_runtime_answer_and_registers_write_intents(monkeypatch):
    import app.api.runs as runs_module  # noqa: WPS433

    monkeypatch.setattr(
        runs_module,
        "execute_run_request",
        lambda request, user_id, trace_id, headers: UnifiedAgentState(
            request=RequestContext(
                trace_id=trace_id,
                user_id=user_id,
                task_type=TaskType.DIAGNOSIS,
                user_message=request.context.user_message or "",
                question_title=request.context.question_title,
                judge_result=request.context.judge_result,
            ),
            execution=ExecutionState(
                run_id="runtime-run",
                graph_name="llm_runtime",
                status=RunStatus.SUCCEEDED,
                active_node="response_packaging",
            ),
            evidence=EvidenceState(route_names=["llm_only"]),
            guardrail=GuardrailState(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
            ),
            outcome=OutcomeState(
                intent="analyze_failure",
                answer="诊断结论：重复值场景下，哈希表更新时机过早。",
                confidence=0.92,
                next_action="先手推 [3,3] 这个样例，再决定什么时候写入当前下标。",
                status_events=[
                    {"node": "llm_prepare", "message": "已整理大模型输入上下文。"},
                    {"node": "llm_inference", "message": "已完成推理。"},
                    {"node": "response_packaging", "message": "已整理模型输出结果。"},
                ],
                write_intents=[
                    WriteIntent(
                        intent_type="profile_update_write",
                        target_service="oj-friend",
                        payload={"focus_tags": ["array"]},
                    )
                ],
            ),
        ),
        raising=False,
    )

    response = client.post(
        "/api/runs",
        json={
            "runType": "interactive_diagnosis",
            "source": "workspace_panel",
            "userId": "u-4",
            "context": {
                "questionTitle": "Two Sum",
                "judgeResult": "WA on sample #2",
                "userMessage": "Why is this still wrong?",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()

    artifacts = client.get(f"/api/runs/{payload['runId']}/artifacts")
    assert artifacts.status_code == 200
    rows = artifacts.json()
    assert len(rows) == 2
    assert rows[0]["title"] == "诊断任务已创建"
    assert rows[1]["artifactType"] == "diagnosis_report"
    assert rows[1]["artifactTypeLabel"] == "诊断报告"
    assert rows[1]["body"]["answer"].startswith("诊断结论：")
    assert rows[1]["body"]["nextAction"] == "先手推 [3,3] 这个样例，再决定什么时候写入当前下标。"
    assert rows[1]["body"]["intentLabel"] == "诊断分析"

    event_response = client.get(f"/api/runs/{payload['runId']}/events")
    assert event_response.status_code == 200
    assert '"eventType": "graph.node_completed"' in event_response.text
    assert '"eventTypeLabel": "节点已完成"' in event_response.text
    assert '"nodeLabel": "上下文整理"' in event_response.text
    assert '"graphName": "llm_runtime"' in event_response.text

    write_intents = run_service.list_write_intents(payload["runId"])
    decisions = run_service.list_policy_decisions(payload["runId"])
    assert len(write_intents) == 1
    assert write_intents[0].intent_type.value == "profile_update"
    assert decisions[0].decision.value == "AUTO_APPLY"


def test_interactive_plan_run_reaches_llm_runtime_and_registers_write_intent(monkeypatch):
    import app.api.runs as runs_module  # noqa: WPS433

    monkeypatch.setattr(
        runs_module,
        "execute_run_request",
        lambda request, user_id, trace_id, headers: UnifiedAgentState(
            request=RequestContext(
                trace_id=trace_id,
                user_id=user_id,
                task_type=TaskType.TRAINING_PLAN,
                user_message=request.context.user_message or "",
                question_title=request.context.question_title,
                judge_result=request.context.judge_result,
            ),
            execution=ExecutionState(
                run_id="runtime-run",
                graph_name="llm_runtime",
                status=RunStatus.SUCCEEDED,
                active_node="training_plan_llm",
            ),
            evidence=EvidenceState(route_names=["llm_only"]),
            guardrail=GuardrailState(
                risk_level=RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
            ),
            outcome=OutcomeState(
                intent="training_plan",
                answer="先练数组和哈希。",
                next_action="先完成第一题。",
                confidence=0.95,
                response_payload={
                    "current_level": "starter",
                    "target_direction": "algorithm_foundation",
                    "weak_points": "hash table",
                    "strong_points": "array basics",
                    "plan_title": "四天入门计划",
                    "plan_goal": "稳定哈希与数组基础。",
                    "ai_summary": "从基础题开始推进。",
                    "tasks": [
                        {
                            "task_type": "question",
                            "question_id": 1001,
                            "exam_id": None,
                            "title_snapshot": "Two Sum",
                            "task_order": 1,
                            "recommended_reason": "先补齐哈希表基本功。",
                            "knowledge_tags_snapshot": "hash table",
                            "due_time": None,
                        }
                    ],
                },
                status_events=[
                    {"node": "llm_prepare", "message": "已整理训练计划生成所需上下文。"},
                    {"node": "llm_inference", "message": "已完成训练计划推理。"},
                    {"node": "training_plan_llm", "message": "已校验并封装训练计划结果。"},
                ],
                write_intents=[
                    WriteIntent(
                        intent_type="training_plan_write",
                        target_service="oj-friend",
                        payload={"plan_title": "四天入门计划"},
                    )
                ],
            ),
        ),
        raising=False,
    )

    response = client.post(
        "/api/runs",
        json={
            "runType": "interactive_plan",
            "source": "workspace_panel",
            "userId": "u-plan",
            "context": {
                "questionId": "1001",
                "questionTitle": "Two Sum",
                "judgeResult": "WA on sample #2",
                "userMessage": "Build a learning plan for me.",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCEEDED"

    artifacts = client.get(f"/api/runs/{payload['runId']}/artifacts")
    assert artifacts.status_code == 200
    rows = artifacts.json()
    assert any(row["artifactType"] == "training_plan" for row in rows)

    write_intents = run_service.list_write_intents(payload["runId"])
    decisions = run_service.list_policy_decisions(payload["runId"])
    assert write_intents
    assert write_intents[0].intent_type.value == "training_plan_recompute"
    assert decisions[0].decision.value == "AUTO_APPLY"


def test_draft_approval_flow_surfaces_through_inbox_and_draft_routes():
    run = run_service.create_run(
        run_type=RunType.PLAN_RECOMPUTE,
        source=RunSource.SCHEDULER,
        user_id="u-3",
    )
    write_intent, _decision = run_service.register_write_intent(
        StoredWriteIntent(
            run_id=run.run_id,
            user_id="u-3",
            intent_type=WriteIntentType.TRAINING_PLAN_REPLACE,
            target_service=TargetService.OJ_FRIEND,
            target_aggregate="training_plan",
            payload={"planTitle": "Replacement plan"},
            user_impact_level=UserImpactLevel.HIGH,
        )
    )

    drafts = run_service.list_drafts("u-3")
    assert drafts

    inbox_response = client.get("/api/inbox", params={"user_id": "u-3"})
    assert inbox_response.status_code == 200
    assert inbox_response.json()[0]["itemType"] == InboxItemType.DRAFT_REVIEW.value

    approve_response = client.post(
        f"/api/drafts/{drafts[0].draft_id}/approve",
        json={"userId": "u-3"},
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"
    assert run_service.list_policy_decisions(run.run_id)[0].write_intent_id == write_intent.write_intent_id
