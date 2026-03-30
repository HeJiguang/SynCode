from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievalQuery:
    query_text: str
    task_type: str
    user_id: str | None = None
    conversation_id: str | None = None


@dataclass(frozen=True)
class RetrievedEvidence:
    evidence_id: str
    route_name: str
    source_type: str
    source_id: str
    title: str
    snippet: str
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    route_names: list[str]
    items: list[RetrievedEvidence]
