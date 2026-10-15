import pytest


@pytest.fixture(autouse=True)
def isolate_local_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("OJ_AGENT_ENV_FILE", str(tmp_path / ".env.test.local"))
    monkeypatch.setenv("OJ_AGENT_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'agent-test.sqlite3'}")
