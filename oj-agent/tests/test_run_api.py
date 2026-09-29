from pathlib import Path
import sys
from contextlib import contextmanager

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.application.run_service import run_service  # noqa: E402
from app.conversations.service import ConversationBusy  # noqa: E402
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
        headers={"X-User-Id": "u-1"},
        json={
            "runType": "interactive_tutor",
            "source": "workspace_panel",
            "userId": "u-1",
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

    run_snapshot = client.get(f"/api/runs/{payload['runId']}", headers={"X-User-Id": "u-1"})
    assert run_snapshot.status_code == 200
    assert run_snapshot.json()["runId"] == payload["runId"]
    assert "contextRef" in run_snapshot.json()

    artifacts = client.get(f"/api/runs/{payload['runId']}/artifacts", headers={"X-User-Id": "u-1"})
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
        headers={"X-User-Id": "u-2"},
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

    event_response = client.get(f"/api/runs/{run_id}/events", headers={"X-User-Id": "u-2"})

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
        headers={"X-User-Id": "u-4"},
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

    artifacts = client.get(f"/api/runs/{payload['runId']}/artifacts", headers={"X-User-Id": "u-4"})
    assert artifacts.status_code == 200
    rows = artifacts.json()
    assert len(rows) == 2
    assert rows[0]["title"] == "诊断任务已创建"
    assert rows[1]["artifactType"] == "diagnosis_report"
    assert rows[1]["artifactTypeLabel"] == "诊断报告"
    assert rows[1]["body"]["answer"].startswith("诊断结论：")
    assert rows[1]["body"]["nextAction"] == "先手推 [3,3] 这个样例，再决定什么时候写入当前下标。"
    assert rows[1]["body"]["intentLabel"] == "诊断分析"

    event_response = client.get(f"/api/runs/{payload['runId']}/events", headers={"X-User-Id": "u-4"})
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
        headers={"X-User-Id": "u-plan"},
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

    artifacts = client.get(f"/api/runs/{payload['runId']}/artifacts", headers={"X-User-Id": "u-plan"})
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

    inbox_response = client.get("/api/inbox", headers={"X-User-Id": "u-3"})
    assert inbox_response.status_code == 200
    assert inbox_response.json()[0]["itemType"] == InboxItemType.DRAFT_REVIEW.value

    approve_response = client.post(
        f"/api/drafts/{drafts[0].draft_id}/approve",
        headers={"X-User-Id": "u-3"},
        json={"userId": "u-3"},
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"
    assert run_service.list_policy_decisions(run.run_id)[0].write_intent_id == write_intent.write_intent_id


def test_gateway_identity_overrides_untrusted_body_user_id(monkeypatch):
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
        headers={"X-User-Id": "trusted-user"},
        json={
            "runType": "interactive_tutor",
            "source": "workspace_panel",
            "userId": "attacker-controlled-user",
            "context": {"userMessage": "给我一个提示。"},
        },
    )

    assert response.status_code == 200
    run = run_service.get_run(response.json()["runId"])
    assert run.user_id == "trusted-user"
    conversation_id = response.json()["conversationId"]
    assert client.get(
        f"/api/conversations/{conversation_id}", headers={"X-User-Id": "trusted-user"}
    ).status_code == 200
    assert client.get(
        f"/api/conversations/{conversation_id}", headers={"X-User-Id": "attacker-controlled-user"}
    ).status_code == 404


def test_run_resources_are_hidden_from_other_users(monkeypatch):
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
    created = client.post(
        "/api/runs",
        headers={"X-User-Id": "run-owner"},
        json={
            "runType": "interactive_tutor",
            "source": "workspace_panel",
            "context": {"userMessage": "解释这道题。"},
        },
    )
    run_id = created.json()["runId"]

    assert client.get(f"/api/runs/{run_id}", headers={"X-User-Id": "other-user"}).status_code == 404
    assert client.get(
        f"/api/runs/{run_id}/artifacts", headers={"X-User-Id": "other-user"}
    ).status_code == 404
    assert client.get(
        f"/api/runs/{run_id}/events", headers={"X-User-Id": "other-user"}
    ).status_code == 404


def test_same_chat_lock_contention_returns_conflict(monkeypatch):
    import app.api.runs as runs_module  # noqa: WPS433

    conversation_service = runs_module.get_conversation_service()
    conversation = conversation_service.get_default("busy-user").conversation

    @contextmanager
    def busy_serialization(_conversation_id, _user_id):
        raise ConversationBusy("当前 Chat 正在处理另一条消息，请稍后重试。")
        yield

    monkeypatch.setattr(conversation_service, "serialized", busy_serialization)
    response = client.post(
        "/api/runs",
        headers={"X-User-Id": "busy-user"},
        json={
            "runType": "interactive_tutor",
            "source": "workspace_panel",
            "conversationId": conversation.conversation_id,
            "context": {"userMessage": "并发请求"},
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "当前 Chat 正在处理另一条消息，请稍后重试。"


def test_github_snapshot_requires_one_time_user_approval(monkeypatch, tmp_path):
    import app.api.runs as runs_module  # noqa: WPS433
    import app.api.tool_approvals as approvals_module  # noqa: WPS433
    import app.conversations.service as conversation_module  # noqa: WPS433

    sha = "d" * 40
    monkeypatch.setenv("OJ_AGENT_RUNTIME_DATA_DIR", str(tmp_path))

    resumed_context = {}

    def fake_execute(request, user_id, trace_id, headers):
        state = _fake_chat_state(
            trace_id,
            user_id,
            request.context.user_message or "",
            request.context.question_title,
            request.context.judge_result,
        )
        if request.context.approved_tool_context:
            resumed_context["tool_context"] = request.context.approved_tool_context
            resumed_context["message"] = request.context.user_message
        state.outcome.response_payload["tool_requests"] = [
            {
                "tool_name": "github.download_snapshot",
                "action": "download",
                "resource": "https://github.com/example/project",
                "arguments": {},
            }
        ]
        return state

    def fake_prepare(request):
        return (
            request.model_copy(update={"arguments": {"commit_sha": sha}}),
            {"repository": request.resource, "commitSha": sha},
        )

    monkeypatch.setattr(runs_module, "execute_run_request", fake_execute)
    monkeypatch.setattr(approvals_module, "execute_run_request", fake_execute)
    monkeypatch.setattr(conversation_module, "prepare_github_snapshot_request", fake_prepare)

    def fake_download(request, **kwargs):
        files_root = tmp_path / "github-snapshots" / kwargs["approval_id"] / "files"
        (files_root / "src").mkdir(parents=True)
        (files_root / "README.md").write_text("# Approved repository\n", encoding="utf-8")
        (files_root / "src" / "main.py").write_text("print('sample')\n", encoding="utf-8")
        return {
            "snapshotId": kwargs["approval_id"],
            "repository": request.resource,
            "commitSha": sha,
            "fileCount": 2,
            "fileSample": ["README.md", "src/main.py"],
            "allowExecution": False,
            "expiresAt": "2099-01-01T00:00:00+00:00",
        }

    monkeypatch.setattr(conversation_module, "download_github_snapshot", fake_download)

    created = client.post(
        "/api/runs",
        headers={"X-User-Id": "github-user"},
        json={
            "runType": "interactive_tutor",
            "source": "workspace_panel",
            "context": {"userMessage": "下载这个仓库供后续分析。"},
        },
    )

    assert created.status_code == 200
    assert created.json()["status"] == "WAITING_USER"
    run_id = created.json()["runId"]
    approvals = client.get(
        f"/api/tool-approvals?runId={run_id}",
        headers={"X-User-Id": "github-user"},
    ).json()
    assert len(approvals) == 1
    assert approvals[0]["status"] == "PENDING"
    assert approvals[0]["arguments"]["commitSha"] == sha

    assert client.post(
        f"/api/tool-approvals/{approvals[0]['approvalId']}/approve",
        headers={"X-User-Id": "other-user"},
    ).status_code == 404

    resolved = client.post(
        f"/api/tool-approvals/{approvals[0]['approvalId']}/approve",
        headers={"X-User-Id": "github-user"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "EXECUTED"
    assert resolved.json()["result"]["allowExecution"] is False
    assert client.get(f"/api/runs/{run_id}", headers={"X-User-Id": "github-user"}).json()["status"] == "SUCCEEDED"
    assert resumed_context["tool_context"][0]["result"]["commitSha"] == sha
    assert "approved_tool_context" in resumed_context["message"]
    assert len(client.get(
        f"/api/tool-approvals?runId={run_id}",
        headers={"X-User-Id": "github-user"},
    ).json()) == 1

    resumed_chat = client.get(
        f"/api/conversations/{created.json()['conversationId']}",
        headers={"X-User-Id": "github-user"},
    ).json()
    assert [message["role"] for message in resumed_chat["messages"]] == ["USER", "ASSISTANT", "ASSISTANT"]

    retried = client.post(
        f"/api/tool-approvals/{approvals[0]['approvalId']}/approve",
        headers={"X-User-Id": "github-user"},
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "EXECUTED"
    assert len(client.get(
        f"/api/conversations/{created.json()['conversationId']}",
        headers={"X-User-Id": "github-user"},
    ).json()["messages"]) == 3

    captured_context = {}

    def fake_followup(request, user_id, trace_id, headers):
        captured_context["tool_context"] = request.context.approved_tool_context
        return _fake_chat_state(
            trace_id,
            user_id,
            request.context.user_message or "",
            request.context.question_title,
            request.context.judge_result,
        )

    monkeypatch.setattr(runs_module, "execute_run_request", fake_followup)
    followup = client.post(
        "/api/runs",
        headers={"X-User-Id": "github-user"},
        json={
            "runType": "interactive_tutor",
            "source": "workspace_panel",
            "conversationId": created.json()["conversationId"],
            "context": {"userMessage": "分析刚才允许读取的仓库。"},
        },
    )

    assert followup.status_code == 200
    assert captured_context["tool_context"][0]["resource"] == "https://github.com/example/project"
    assert captured_context["tool_context"][0]["result"]["commitSha"] == sha
    assert captured_context["tool_context"][0]["text_excerpts"] == [
        {"path": "README.md", "content": "# Approved repository\n"},
        {"path": "src/main.py", "content": "print('sample')\n"},
    ]


def test_denied_tool_request_resumes_without_repository_context(monkeypatch):
    import app.api.runs as runs_module  # noqa: WPS433
    import app.api.tool_approvals as approvals_module  # noqa: WPS433
    import app.conversations.service as conversation_module  # noqa: WPS433

    sha = "e" * 40
    resumed = {}

    def fake_execute(request, user_id, trace_id, headers):
        state = _fake_chat_state(
            trace_id,
            user_id,
            request.context.user_message or "",
            request.context.question_title,
            request.context.judge_result,
        )
        if (request.context.user_message or "").startswith("工具请求已被用户拒绝"):
            resumed["message"] = request.context.user_message
            resumed["tool_context"] = request.context.approved_tool_context
        else:
            state.outcome.response_payload["tool_requests"] = [
                {
                    "tool_name": "github.download_snapshot",
                    "action": "download",
                    "resource": "https://github.com/example/denied",
                    "arguments": {},
                }
            ]
        return state

    monkeypatch.setattr(runs_module, "execute_run_request", fake_execute)
    monkeypatch.setattr(approvals_module, "execute_run_request", fake_execute)
    monkeypatch.setattr(
        conversation_module,
        "prepare_github_snapshot_request",
        lambda request: (
            request.model_copy(update={"arguments": {"commit_sha": sha}}),
            {"repository": request.resource, "commitSha": sha},
        ),
    )

    created = client.post(
        "/api/runs",
        headers={"X-User-Id": "deny-user"},
        json={
            "runType": "interactive_tutor",
            "source": "workspace_panel",
            "context": {"userMessage": "读取仓库后给我建议。"},
        },
    ).json()
    approval = client.get(
        f"/api/tool-approvals?runId={created['runId']}",
        headers={"X-User-Id": "deny-user"},
    ).json()[0]

    denied = client.post(
        f"/api/tool-approvals/{approval['approvalId']}/deny",
        headers={"X-User-Id": "deny-user"},
    )

    assert denied.status_code == 200
    assert denied.json()["status"] == "DENIED"
    assert resumed["tool_context"] == []
    assert "原始用户请求：读取仓库后给我建议。" in resumed["message"]
    assert client.get(
        f"/api/runs/{created['runId']}",
        headers={"X-User-Id": "deny-user"},
    ).json()["status"] == "SUCCEEDED"
