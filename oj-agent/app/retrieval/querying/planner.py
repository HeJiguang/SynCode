from app.retrieval.models import RetrievalQuery


class RetrievalRoutePlanner:
    def plan(self, query: RetrievalQuery) -> list[str]:
        route_map = {
            "chat": ["lexical", "dense", "personalized"],
            "diagnosis": ["lexical", "dense"],
            "recommendation": ["lexical", "dense", "personalized"],
            "training_plan": ["lexical", "dense", "personalized"],
            "review": ["lexical", "dense", "personalized"],
            "profile": ["lexical", "dense", "personalized"],
        }
        return list(route_map.get(query.task_type, ["lexical", "dense"]))
