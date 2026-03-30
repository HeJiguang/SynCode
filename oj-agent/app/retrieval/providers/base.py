from typing import Protocol

from app.retrieval.models import RetrievedEvidence, RetrievalQuery


class RetrievalProvider(Protocol):
    route_name: str

    def retrieve(self, query: RetrievalQuery) -> list[RetrievedEvidence]: ...
