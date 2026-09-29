import pytest


@pytest.fixture(autouse=True)
def isolate_local_env_file(monkeypatch, tmp_path):
    monkeypatch.setenv("OJ_AGENT_ENV_FILE", str(tmp_path / ".env.test.local"))
    monkeypatch.setenv("OJ_AGENT_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'agent-test.sqlite3'}")
    monkeypatch.setenv("HOST_IP", "127.0.0.1")
    from app.conversations.service import reset_conversation_service

    reset_conversation_service()
    yield
    reset_conversation_service()
