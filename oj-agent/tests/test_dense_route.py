from app.retrieval.models import RetrievalQuery
from app.retrieval.routes.dense import DenseRoute


def test_dense_route_returns_qdrant_evidence_when_enabled(monkeypatch):
    route = DenseRoute()

    monkeypatch.setattr(route, "_is_enabled", lambda: True, raising=False)
    monkeypatch.setattr(route, "_ensure_index_ready", lambda: None, raising=False)
    monkeypatch.setattr(route, "_embed_query", lambda query_text: [1.0, 0.0, 0.0, 0.0], raising=False)
    monkeypatch.setattr(
        route,
        "_search_qdrant",
        lambda vector, limit: [
            {
                "id": "dense-1",
                "score": 0.97,
                "payload": {
                    "source": "algorithm-docs/hash-map-patterns.md",
                    "title": "Hash Map Patterns",
                    "snippet": "Use a hash map to store complements.",
                },
            }
        ],
        raising=False,
    )

    result = route.retrieve(
        RetrievalQuery(
            query_text="two sum wrong answer",
            task_type="chat",
            user_id="u-1",
        )
    )

    assert len(result) == 1
    assert result[0].route_name == "dense"
    assert result[0].source_id == "algorithm-docs/hash-map-patterns.md"
    assert result[0].title == "Hash Map Patterns"
    assert result[0].snippet == "Use a hash map to store complements."
    assert result[0].score == 0.97
