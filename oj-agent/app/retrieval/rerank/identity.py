from app.retrieval.models import RetrievedEvidence, RetrievalQuery
from app.retrieval.rerank.base import BaseReranker


class IdentityReranker(BaseReranker):
    def rerank(self, query: RetrievalQuery, items: list[RetrievedEvidence]) -> list[RetrievedEvidence]:
        return list(items)
