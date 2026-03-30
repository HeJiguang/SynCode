from abc import ABC, abstractmethod

from app.retrieval.models import RetrievedEvidence, RetrievalQuery


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: RetrievalQuery, items: list[RetrievedEvidence]) -> list[RetrievedEvidence]:
        raise NotImplementedError
