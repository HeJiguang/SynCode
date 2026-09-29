import pytest
from fastapi.testclient import TestClient

from app.application.run_admission import (
    RunAdmissionError,
    RunExecutionSlotTimeout,
    RunExecutionSlotLimiter,
    create_admitted_run,
)
from app.application.run_service import run_service
from app.domain.runs import ContextRef, EventType, RunSource, RunStatus, RunType
from app.main import app


client = TestClient(app)


def setup_function():
    run_service.clear()


def _create(**overrides):
    payload = {
        "run_type": RunType.INTERACTIVE_TUTOR,
        "source": RunSource.WORKSPACE_PANEL,
        "user_id": "quota-user",
        "conversation_id": "conv_quota",
        "context_ref": ContextRef(question_id="42"),
        "request_payload": {"context": {"userMessage": "help"}},
        "queue_for_execution": True,
    }
    payload.update(overrides)
    return create_admitted_run(run_service, **payload)


def test_user_active_run_limit_rejects_and_records_audit_event(monkeypatch):
    monkeypatch.setenv("OJ_AGENT_USER_MAX_ACTIVE_RUNS", "1")
    monkeypatch.setenv("OJ_AGENT_USER_RUN_RATE_LIMIT_PER_MINUTE", "0")

    first = _create()
    assert first.status is RunStatus.QUEUED
    assert any(event.event_type is EventType.RUN_QUEUED for event in run_service.list_events(first.run_id))

    with pytest.raises(RunAdmissionError) as exc_info:
        _create()

    rejected = run_service.get_run(exc_info.value.run_id)
    assert rejected.status is RunStatus.FAILED
    assert any(
        event.event_type is EventType.RESOURCE_LIMIT_REJECTED
        for event in run_service.list_events(rejected.run_id)
    )


def test_user_run_rate_limit_counts_rejected_attempts(monkeypatch):
    monkeypatch.setenv("OJ_AGENT_USER_MAX_ACTIVE_RUNS", "0")
    monkeypatch.setenv("OJ_AGENT_USER_RUN_RATE_LIMIT_PER_MINUTE", "1")

    assert _create().status is RunStatus.QUEUED
    with pytest.raises(RunAdmissionError) as exc_info:
        _create()

    assert exc_info.value.status_code == 429
    assert run_service.get_run(exc_info.value.run_id).status is RunStatus.FAILED


def test_run_api_maps_rate_limit_to_retryable_response(monkeypatch):
    monkeypatch.setenv("OJ_AGENT_USER_MAX_ACTIVE_RUNS", "0")
    monkeypatch.setenv("OJ_AGENT_USER_RUN_RATE_LIMIT_PER_MINUTE", "1")
    _create(user_id="api-quota-user", conversation_id=None)

    response = client.post(
        "/api/runs",
        headers={"X-User-Id": "api-quota-user"},
        json={
            "runType": "interactive_tutor",
            "source": "workspace_panel",
            "context": {"userMessage": "help"},
        },
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert "每分钟最多" in response.json()["detail"]


def test_global_execution_slot_times_out_and_releases(monkeypatch):
    monkeypatch.setenv("OJ_AGENT_GLOBAL_MAX_CONCURRENT_RUNS", "1")
    monkeypatch.setenv("OJ_AGENT_RUN_ADMISSION_WAIT_SECONDS", "0")
    monkeypatch.setattr("app.core.config._resolve_default_nacos_ip", lambda: "127.0.0.1")

    limiter = RunExecutionSlotLimiter()
    with limiter.slot():
        with pytest.raises(RunExecutionSlotTimeout):
            with limiter.slot():
                pass

    with limiter.slot():
        pass
