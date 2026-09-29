import pytest
from fastapi.testclient import TestClient

from app.conversations import get_conversation_service
from app.conversations.service import ConversationLimitReached
from app.domain.conversations import ConversationStatus
from app.domain.tool_permissions import ToolApprovalStatus
from app.main import app


client = TestClient(app)


def test_default_chat_is_stable_while_user_switches_questions():
    service = get_conversation_service()
    first = service.get_default("2001").conversation

    service.append_user_message(
        first.conversation_id,
        "2001",
        content="先提示我这道数组题。",
        run_id="run-a",
        question_id="101",
        question_title="数组题",
        context_snapshot={"question_id": "101", "user_code": "class A {}"},
    )
    service.append_user_message(
        first.conversation_id,
        "2001",
        content="现在我切到图论题了。",
        run_id="run-b",
        question_id="202",
        question_title="图论题",
        context_snapshot={"question_id": "202", "user_code": "class B {}"},
    )

    second = service.get_default("2001")
    assert second.conversation.conversation_id == first.conversation_id
    assert second.conversation.current_question_id == "202"
    assert [message.question_id for message in second.messages] == ["101", "202"]


def test_rollover_only_inherits_memories_selected_by_user():
    service = get_conversation_service()
    original = service.get_default("2002").conversation
    approved = service.repository.create_memory_candidate(
        "2002",
        memory_type="preference",
        content="用户希望先获得提示，不直接看完整答案。",
        reason="用户明确表达过该偏好。",
        confidence=0.99,
        source_conversation_id=original.conversation_id,
        source_message_id=None,
    )
    unselected = service.repository.create_memory_candidate(
        "2002",
        memory_type="learning_observation",
        content="用户可能不熟悉并查集。",
        reason="仅依据一次失败推测。",
        confidence=0.55,
        source_conversation_id=original.conversation_id,
        source_message_id=None,
    )

    continuation = service.create_continuation(
        "2002",
        continued_from_conversation_id=original.conversation_id,
        memory_ids=[approved.memory_id],
    )

    assert continuation.conversation.is_default is True
    assert [item.memory_id for item in continuation.context_memories] == [approved.memory_id]
    assert unselected.memory_id not in [item.memory_id for item in continuation.context_memories]
    assert service.get_snapshot(original.conversation_id, "2002").conversation.status is ConversationStatus.ROLLED_OVER


def test_rolled_over_chat_rejects_new_messages_and_runs():
    service = get_conversation_service()
    original = service.get_default("2002-read-only").conversation
    service.create_continuation(
        "2002-read-only",
        continued_from_conversation_id=original.conversation_id,
        memory_ids=[],
    )

    with pytest.raises(ConversationLimitReached, match="历史 Chat 只能查看"):
        service.append_user_message(
            original.conversation_id,
            "2002-read-only",
            content="继续旧对话",
            run_id="run-old-chat",
            question_id="202",
            question_title="旧题目",
            context_snapshot={},
        )

    response = client.post(
        "/api/runs",
        headers={"X-User-Id": "2002-read-only"},
        json={
            "runType": "interactive_tutor",
            "source": "workspace_panel",
            "conversationId": original.conversation_id,
            "context": {"userMessage": "继续旧对话"},
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "历史 Chat 只能查看，请在当前默认 Chat 中继续。"


def test_hard_context_limit_requires_a_new_chat(monkeypatch):
    service = get_conversation_service()
    service.hard_token_limit = 3
    service.soft_token_limit = 2
    conversation = service.get_default("2003").conversation

    service.append_user_message(
        conversation.conversation_id,
        "2003",
        content="这段内容会超过非常小的测试预算。",
        run_id="run-limit",
        question_id="303",
        question_title="预算测试",
        context_snapshot={},
    )

    with pytest.raises(ConversationLimitReached):
        service.append_user_message(
            conversation.conversation_id,
            "2003",
            content="继续",
            run_id="run-limit-2",
            question_id="303",
            question_title="预算测试",
            context_snapshot={},
        )


def test_conversation_api_hides_other_users_chats():
    owner = client.get("/api/conversations/default", headers={"X-User-Id": "3001"})
    assert owner.status_code == 200
    conversation_id = owner.json()["conversation"]["conversationId"]

    forbidden = client.get(
        f"/api/conversations/{conversation_id}",
        headers={"X-User-Id": "3002"},
    )

    assert forbidden.status_code == 404


def test_blocked_hermes_tool_decision_is_persisted_and_user_scoped():
    service = get_conversation_service()
    conversation = service.get_default("tool-owner").conversation

    approvals = service.record_runtime_tool_decisions(
        "tool-owner",
        conversation.conversation_id,
        "run-tool-1",
        [
            {
                "hermes_run_id": "hermes-run-1",
                "hermes_request_id": "request-1",
                "tool_name": "host.shell",
                "action": "execute",
                "resource": "git clone https://github.com/example/project",
                "arguments": {"description": "download repository"},
            }
        ],
    )

    assert approvals[0].status is ToolApprovalStatus.DENIED
    assert approvals[0].decision.value == "BLOCK"
    owner_response = client.get(
        "/api/tool-approvals?runId=run-tool-1",
        headers={"X-User-Id": "tool-owner"},
    )
    other_response = client.get(
        "/api/tool-approvals?runId=run-tool-1",
        headers={"X-User-Id": "other-user"},
    )
    assert owner_response.status_code == 200
    assert owner_response.json()[0]["status"] == "DENIED"
    assert other_response.status_code == 200
    assert other_response.json() == []
