from app.retrieval.models import RetrievedEvidence, RetrievalQuery
from app.retrieval.runtime import RetrievalRuntime


def test_retrieval_runtime_returns_normalized_evidence_from_routes(monkeypatch):
    runtime = RetrievalRuntime()

    monkeypatch.setattr(
        runtime.lexical_route,
        "retrieve",
        lambda query: [
            RetrievedEvidence(
                evidence_id="lex-1",
                route_name="lexical",
                source_type="knowledge_doc",
                source_id="doc-1",
                title="Hash Map Patterns",
                snippet="Use a hash map to track complements.",
                score=0.92,
            )
        ],
    )
    monkeypatch.setattr(runtime.dense_route, "retrieve", lambda query: [])
    monkeypatch.setattr(runtime.personalized_route, "retrieve", lambda query: [])

    result = runtime.retrieve(
        RetrievalQuery(
            query_text="two sum wrong answer",
            task_type="chat",
        )
    )

    assert result.route_names == ["lexical"]
    assert len(result.items) == 1
    assert result.items[0].source_id == "doc-1"
    assert result.items[0].route_name == "lexical"


def test_retrieval_runtime_returns_empty_result_for_blank_query():
    runtime = RetrievalRuntime()

    result = runtime.retrieve(
        RetrievalQuery(
            query_text="   ",
            task_type="chat",
        )
    )

    assert result.route_names == []
    assert result.items == []


def test_retrieval_runtime_fuses_routes_and_applies_rerank(monkeypatch):
    runtime = RetrievalRuntime()

    monkeypatch.setattr(
        runtime.lexical_route,
        "retrieve",
        lambda query: [
            RetrievedEvidence(
                evidence_id="lex-1",
                route_name="lexical",
                source_type="knowledge_doc",
                source_id="doc-lex",
                title="Array Basics",
                snippet="Trace indexes carefully.",
                score=0.61,
            )
        ],
    )
    monkeypatch.setattr(
        runtime.dense_route,
        "retrieve",
        lambda query: [
            RetrievedEvidence(
                evidence_id="dense-1",
                route_name="dense",
                source_type="knowledge_doc",
                source_id="doc-dense",
                title="Hash Map Patterns",
                snippet="Use a hash map to track complements.",
                score=0.73,
            )
        ],
    )
    monkeypatch.setattr(runtime.personalized_route, "retrieve", lambda query: [])

    assert hasattr(runtime, "reranker")

    monkeypatch.setattr(
        runtime.reranker,
        "rerank",
        lambda query, items: list(reversed(items)),
    )

    result = runtime.retrieve(
        RetrievalQuery(
            query_text="two sum wrong answer",
            task_type="diagnosis",
        )
    )

    assert result.route_names == ["lexical", "dense"]
    assert len(result.items) == 2
    assert result.items[0].source_id == "doc-lex"


def test_retrieval_runtime_uses_task_specific_route_plan(monkeypatch):
    runtime = RetrievalRuntime()
    route_calls: list[str] = []

    monkeypatch.setattr(
        runtime.lexical_route,
        "retrieve",
        lambda query: route_calls.append("lexical") or [],
    )
    monkeypatch.setattr(
        runtime.dense_route,
        "retrieve",
        lambda query: route_calls.append("dense") or [],
    )
    monkeypatch.setattr(
        runtime.personalized_route,
        "retrieve",
        lambda query: route_calls.append("personalized") or [],
    )

    runtime.retrieve(
        RetrievalQuery(
            query_text="what should I practice next",
            task_type="recommendation",
        )
    )

    assert route_calls == ["lexical", "dense", "personalized"]


def test_retrieval_runtime_skips_personalized_route_for_diagnosis(monkeypatch):
    runtime = RetrievalRuntime()
    route_calls: list[str] = []

    monkeypatch.setattr(
        runtime.lexical_route,
        "retrieve",
        lambda query: route_calls.append("lexical") or [],
    )
    monkeypatch.setattr(
        runtime.dense_route,
        "retrieve",
        lambda query: route_calls.append("dense") or [],
    )
    monkeypatch.setattr(
        runtime.personalized_route,
        "retrieve",
        lambda query: route_calls.append("personalized") or [],
    )

    runtime.retrieve(
        RetrievalQuery(
            query_text="why is this wa",
            task_type="diagnosis",
        )
    )

    assert route_calls == ["lexical", "dense"]


def test_retrieval_runtime_deduplicates_same_evidence_across_routes(monkeypatch):
    runtime = RetrievalRuntime()

    monkeypatch.setattr(
        runtime.lexical_route,
        "retrieve",
        lambda query: [
            RetrievedEvidence(
                evidence_id="lex-1",
                route_name="lexical",
                source_type="knowledge_doc",
                source_id="doc-shared",
                title="Shared Doc",
                snippet="Use a frequency map and verify bounds.",
                score=0.64,
            )
        ],
    )
    monkeypatch.setattr(
        runtime.dense_route,
        "retrieve",
        lambda query: [
            RetrievedEvidence(
                evidence_id="dense-1",
                route_name="dense",
                source_type="knowledge_doc",
                source_id="doc-shared",
                title="Shared Doc",
                snippet="Use a frequency map and verify bounds.",
                score=0.87,
            )
        ],
    )
    monkeypatch.setattr(runtime.personalized_route, "retrieve", lambda query: [])

    result = runtime.retrieve(
        RetrievalQuery(
            query_text="how do I debug this wrong answer",
            task_type="chat",
        )
    )

    assert result.route_names == ["lexical", "dense"]
    assert len(result.items) == 1
    assert result.items[0].source_id == "doc-shared"
    assert result.items[0].score == 0.87
    assert result.items[0].metadata["matched_routes"] == ["dense", "lexical"]
