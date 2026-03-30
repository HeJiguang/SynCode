from app.retrieval.models import RetrievedEvidence, RetrievalQuery
from app.retrieval.qdrant_indexer import QdrantKnowledgeIndexer


class DenseRoute:
    route_name = "dense"

    def __init__(self, indexer: QdrantKnowledgeIndexer | None = None) -> None:
        self._indexer = indexer or QdrantKnowledgeIndexer()

    def retrieve(self, query: RetrievalQuery) -> list[RetrievedEvidence]:
        if not query.query_text.strip() or not self._is_enabled():
            return []

        try:
            self._ensure_index_ready()
            vector = self._embed_query(query.query_text)
            raw_hits = self._search_qdrant(vector, self._indexer.settings.qdrant_top_k)
        except Exception:
            return []

        items: list[RetrievedEvidence] = []
        for index, hit in enumerate(raw_hits, start=1):
            payload = dict(hit.get("payload") or {})
            items.append(
                RetrievedEvidence(
                    evidence_id=str(hit.get("id") or f"dense-{index}"),
                    route_name=self.route_name,
                    source_type="knowledge_doc",
                    source_id=str(payload.get("source") or f"dense-source-{index}"),
                    title=str(payload.get("title") or "Dense retrieval hit"),
                    snippet=str(payload.get("snippet") or ""),
                    score=float(hit.get("score") or 0.0),
                    metadata={"provider": "qdrant"},
                )
            )
        return items

    def _is_enabled(self) -> bool:
        return self._indexer.is_enabled()

    def _ensure_index_ready(self) -> None:
        self._indexer.ensure_index_ready()

    def _embed_query(self, query_text: str) -> list[float]:
        return self._indexer.embed_text(query_text)

    def _search_qdrant(self, vector: list[float], limit: int) -> list[dict]:
        return self._indexer.search_by_vector(vector, limit)


def bootstrap_dense_index() -> None:
    DenseRoute()._ensure_index_ready()
