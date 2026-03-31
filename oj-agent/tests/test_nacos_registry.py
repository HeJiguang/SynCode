import json

from app.core.config import AgentSettings
from app.core.nacos_registry import NacosRegistry


class _DummyResponse:
    def raise_for_status(self) -> None:
        return None


class _DummyClient:
    def __init__(self) -> None:
        self.post_calls: list[tuple[str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, params: dict | None = None, data: dict | None = None) -> _DummyResponse:
        self.post_calls.append((url, params or data or {}))
        return _DummyResponse()


def _settings() -> AgentSettings:
    return AgentSettings(
        port=8015,
        llm_provider="openai_compatible",
        llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        llm_api_key="test-key",
        chat_model="qwen-turbo",
        training_model="qwen-plus",
        embedding_provider="openai_compatible",
        embedding_model="text-embedding-v3",
        embedding_dimensions=256,
        llm_timeout_seconds=30.0,
        llm_temperature=0.2,
        llm_max_tokens=1200,
        llm_enabled=True,
        llm_fallback_enabled=True,
        gateway_user_id_header="X-User-Id",
        rag_enabled=True,
        rag_doc_globs=(),
        rag_top_k=3,
        rag_max_snippet_chars=420,
        qdrant_enabled=False,
        qdrant_url=None,
        qdrant_api_key=None,
        qdrant_collection="oj-agent-knowledge",
        qdrant_top_k=3,
        qdrant_chunk_size=240,
        nacos_config_enabled=True,
        nacos_config_data_id="oj-agent-local.yaml",
        nacos_enabled=True,
        nacos_server_addr="http://localhost:8848",
        nacos_namespace="test-namespace",
        nacos_group="DEFAULT_GROUP",
        nacos_username=None,
        nacos_password=None,
        nacos_service_name="oj-agent",
        nacos_ip="127.0.0.1",
        nacos_port=8015,
    )


def test_register_posts_instance_and_starts_heartbeat(monkeypatch):
    client = _DummyClient()
    registry = NacosRegistry(_settings())
    started: list[bool] = []

    monkeypatch.setattr("app.core.nacos_registry.httpx.Client", lambda timeout: client)
    monkeypatch.setattr(registry, "_start_heartbeat_loop", lambda: started.append(True))

    registry.register()

    assert started == [True]
    assert client.post_calls
    url, params = client.post_calls[0]
    assert url.endswith("/nacos/v1/ns/instance")
    assert params["serviceName"] == "oj-agent"
    assert params["namespaceId"] == "test-namespace"


def test_heartbeat_params_include_beat_payload():
    registry = NacosRegistry(_settings())

    params = registry._heartbeat_params(None)

    beat = json.loads(params["beat"])
    assert beat["serviceName"] == "oj-agent"
    assert beat["ip"] == "127.0.0.1"
    assert beat["port"] == 8015
    assert beat["scheduled"] is True
