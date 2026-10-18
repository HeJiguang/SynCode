from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_up():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_ready_endpoint_reports_configured_hermes_runtime(monkeypatch):
    monkeypatch.setenv("OJ_AGENT_RUNTIME_PROVIDER", "hermes")
    monkeypatch.setenv("OJ_AGENT_RUNTIME_FALLBACK_TO_DIRECT", "false")
    monkeypatch.setenv("OJ_AGENT_HERMES_BASE_URL", "http://hermes:8642")
    monkeypatch.setenv("OJ_AGENT_HERMES_API_KEY", "hermes-key")
    monkeypatch.setenv(
        "OJ_AGENT_HERMES_PROVISION_URL",
        "http://oj-agent-tools:8016/internal/profiles/ensure",
    )
    monkeypatch.setenv("OJ_AGENT_HERMES_PROVISION_KEY", "provision-key")
    monkeypatch.setenv("OJ_AGENT_HERMES_TRAINING_MODEL", "deepseek-chat")

    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "READY"}


def test_ready_endpoint_rejects_incomplete_hermes_runtime(monkeypatch):
    monkeypatch.setenv("OJ_AGENT_RUNTIME_PROVIDER", "hermes")
    monkeypatch.setenv("OJ_AGENT_RUNTIME_FALLBACK_TO_DIRECT", "false")
    monkeypatch.setenv("OJ_AGENT_HERMES_BASE_URL", "http://hermes:8642")
    monkeypatch.setenv("OJ_AGENT_HERMES_API_KEY", "hermes-key")
    monkeypatch.setenv("OJ_AGENT_HERMES_TRAINING_MODEL", "deepseek-chat")
    monkeypatch.delenv("OJ_AGENT_HERMES_PROVISION_URL", raising=False)
    monkeypatch.delenv("OJ_AGENT_HERMES_PROVISION_KEY", raising=False)

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "NOT_READY"
