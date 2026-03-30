from app.retrieval.models import RetrievalQuery, RetrievalResult, RetrievedEvidence
from app.retrieval.fusion import deduplicate_evidence
from app.retrieval.providers import DenseProvider, LexicalProvider, PersonalizedProvider
from app.retrieval.querying import RetrievalRoutePlanner
from app.retrieval.rerank import IdentityReranker


class RetrievalRuntime:
    def __init__(self) -> None:
        self.route_planner = RetrievalRoutePlanner()
        self.providers = {
            "lexical": LexicalProvider(),
            "dense": DenseProvider(),
            "personalized": PersonalizedProvider(),
        }
        self.lexical_route = self.providers["lexical"]
        self.dense_route = self.providers["dense"]
        self.personalized_route = self.providers["personalized"]
        self.reranker = IdentityReranker()

    def _fuse_route_items(
        self,
        route_items: list[tuple[str, list[RetrievedEvidence]]],
    ) -> list[RetrievedEvidence]:
        merged_items: list[RetrievedEvidence] = []
        for _name, items in route_items:
            merged_items.extend(items)
        merged_items = deduplicate_evidence(merged_items)
        merged_items.sort(key=lambda item: item.score or 0.0, reverse=True)
        return merged_items

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        if not query.query_text.strip():
            return RetrievalResult(route_names=[], items=[])

        planned_routes = self.route_planner.plan(query)
        route_items = [
            (route_name, self.providers[route_name].retrieve(query))
            for route_name in planned_routes
        ]
        route_names = [name for name, items in route_items if items]
        fused_items = self._fuse_route_items(route_items)
        reranked_items = self.reranker.rerank(query, fused_items)
        return RetrievalResult(route_names=route_names, items=reranked_items)
