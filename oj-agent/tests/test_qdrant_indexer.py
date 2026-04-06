from app.core.config import AgentSettings
from app.retrieval.qdrant_indexer import QdrantKnowledgeIndexer


def test_qdrant_indexer_supports_local_hash_embeddings():
    settings = AgentSettings(
        port=8015,
        llm_provider="openai_compatible",
        llm_base_url=None,
        llm_api_key=None,
        chat_model="qwen-turbo",
        training_model="qwen-plus",
        embedding_provider="local_hash",
        embedding_model=None,
        embedding_dimensions=8,
        llm_timeout_seconds=30.0,
        llm_temperature=0.2,
        llm_max_tokens=1200,
        llm_enabled=False,
        gateway_user_id_header="X-User-Id",
        rag_enabled=True,
        rag_doc_globs=("docs/*.md",),
        rag_top_k=3,
        rag_max_snippet_chars=420,
        qdrant_enabled=True,
        qdrant_url="http://127.0.0.1:6333",
        qdrant_api_key=None,
        qdrant_collection="oj-agent-knowledge",
        qdrant_top_k=3,
        qdrant_chunk_size=240,
        nacos_config_enabled=False,
        nacos_config_data_id="oj-agent-local.yaml",
        nacos_enabled=False,
        nacos_server_addr=None,
        nacos_namespace=None,
        nacos_group="DEFAULT_GROUP",
        nacos_username=None,
        nacos_password=None,
        nacos_service_name="oj-agent",
        nacos_ip="127.0.0.1",
        nacos_port=8015,
    )

    indexer = QdrantKnowledgeIndexer(settings)
    vector_a = indexer.embed_text("hash map complement search")
    vector_b = indexer.embed_text("hash map complement search")
    vector_c = indexer.embed_text("binary search midpoint")

    assert indexer.is_enabled() is True
    assert len(vector_a) == 8
    assert vector_a == vector_b
    assert vector_a != vector_c
