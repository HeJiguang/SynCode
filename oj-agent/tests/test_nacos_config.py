from app.core.nacos_config import load_nacos_config


class _DummyResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"accessToken": "test-token"}


class _DummyClient:
    def __init__(self) -> None:
        self.timeout: float | None = None
        self.trust_env: bool | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, data: dict | None = None) -> _DummyResponse:
        return _DummyResponse('{"accessToken":"test-token"}')

    def get(self, url: str, params: dict | None = None) -> _DummyResponse:
        return _DummyResponse("server:\n  port: 8015\n")


def test_load_nacos_config_uses_direct_http_client(monkeypatch):
    client = _DummyClient()

    def _build_client(*, timeout, trust_env):
        client.timeout = timeout
        client.trust_env = trust_env
        return client

    monkeypatch.setenv("OJ_AGENT_NACOS_SERVER_ADDR", "http://localhost:8848")
    monkeypatch.setenv("OJ_AGENT_NACOS_CONFIG_ENABLED", "true")
    monkeypatch.setenv("OJ_AGENT_NACOS_USERNAME", "nacos")
    monkeypatch.setenv("OJ_AGENT_NACOS_PASSWORD", "nacos")
    monkeypatch.setattr("app.core.nacos_config.httpx.Client", _build_client)

    payload = load_nacos_config()

    assert client.timeout is not None
    assert client.trust_env is False
    assert payload["data"]["server"]["port"] == 8015
