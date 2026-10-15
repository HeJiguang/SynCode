from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from threading import Lock
from typing import Iterable

import httpx

from app.learning_memory.models import MemoryLevel
from app.skill_governance.search import EmbeddingClient, SkillSearchError


@dataclass(frozen=True)
class IndexedLearningMemory:
    memory_id: str
    owner_hash: str
    level: MemoryLevel
    memory_type: str
    title: str
    summary: str
    knowledge_tags: tuple[str, ...]
    error_type: str | None
    status: str
    confidence: float
    occurrence_count: int
    occurred_at: datetime | None
    last_seen_at: datetime | None

    @property
    def embedding_text(self) -> str:
        return "\n".join(
            part for part in (
                self.title,
                self.summary,
                " ".join(self.knowledge_tags),
                self.error_type or "",
            ) if part
        )


class LearningMemoryIndex:
    """User-scoped hybrid index for derived learning memories."""

    def __init__(self, embedder: EmbeddingClient | None = None) -> None:
        self.base_url = (
            os.getenv("SYNCODE_ELASTICSEARCH_URL")
            or os.getenv("SPRING_ELASTICSEARCH_URIS")
            or ""
        ).strip().rstrip("/")
        self.index_name = os.getenv("SYNCODE_LEARNING_MEMORY_INDEX", "syncode-learning-memory-v1").strip()
        self.embedder = embedder or EmbeddingClient()
        self.min_rrf_score = float(os.getenv("SYNCODE_LEARNING_MEMORY_MIN_RRF_SCORE", "0.012"))
        self._replace_lock = Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.embedder.enabled)

    def ensure_index(self) -> None:
        if not self.enabled:
            raise SkillSearchError("Learning memory hybrid indexing is not fully configured.")
        mapping = {
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "memory_id": {"type": "keyword"},
                    "owner_hash": {"type": "keyword"},
                    "memory_level": {"type": "keyword"},
                    "memory_type": {"type": "keyword"},
                    "title": {"type": "text"},
                    "summary": {"type": "text"},
                    "knowledge_tags": {"type": "keyword"},
                    "error_type": {"type": "keyword"},
                    "memory_status": {"type": "keyword"},
                    "confidence": {"type": "float"},
                    "occurrence_count": {"type": "integer"},
                    "occurred_at": {"type": "date"},
                    "last_seen_at": {"type": "date"},
                    "content_vector": {
                        "type": "dense_vector",
                        "dims": self.embedder.dimensions,
                        "index": True,
                        "similarity": "cosine",
                    },
                },
            }
        }
        with httpx.Client(timeout=15.0) as client:
            response = client.head(f"{self.base_url}/{self.index_name}")
            if response.status_code == 404:
                created = client.put(f"{self.base_url}/{self.index_name}", json=mapping)
                created.raise_for_status()
            elif response.is_error:
                response.raise_for_status()

    def replace_user(self, owner_hash: str, rows: Iterable[IndexedLearningMemory]) -> int:
        memories = list(rows)
        with self._replace_lock:
            self.ensure_index()
            with httpx.Client(timeout=30.0) as client:
                deleted = client.post(
                    f"{self.base_url}/{self.index_name}/_delete_by_query?refresh=true&conflicts=proceed",
                    json={"query": {"term": {"owner_hash": owner_hash}}},
                )
                deleted.raise_for_status()
            if not memories:
                return 0
            vectors = self.embedder.embed([memory.embedding_text for memory in memories])
            lines: list[str] = []
            for memory, vector in zip(memories, vectors, strict=True):
                lines.append(json.dumps({"index": {"_index": self.index_name, "_id": memory.memory_id}}))
                lines.append(json.dumps({
                    "memory_id": memory.memory_id,
                    "owner_hash": memory.owner_hash,
                    "memory_level": memory.level,
                    "memory_type": memory.memory_type,
                    "title": memory.title,
                    "summary": memory.summary,
                    "knowledge_tags": memory.knowledge_tags,
                    "error_type": memory.error_type,
                    "memory_status": memory.status,
                    "confidence": memory.confidence,
                    "occurrence_count": memory.occurrence_count,
                    "occurred_at": memory.occurred_at.isoformat() if memory.occurred_at else None,
                    "last_seen_at": memory.last_seen_at.isoformat() if memory.last_seen_at else None,
                    "content_vector": vector,
                }, ensure_ascii=False))
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/_bulk?refresh=true",
                    headers={"Content-Type": "application/x-ndjson"},
                    content=("\n".join(lines) + "\n").encode(),
                )
                response.raise_for_status()
                if response.json().get("errors"):
                    raise SkillSearchError("Elasticsearch rejected one or more learning memories.")
            return len(memories)

    def search(
        self,
        *,
        owner_hash: str,
        query: str,
        levels: tuple[MemoryLevel, ...],
        knowledge_tags: tuple[str, ...],
        time_range_days: int,
        limits: dict[MemoryLevel, int],
    ) -> dict[MemoryLevel, list[str]]:
        self.ensure_index()
        vector = self.embedder.embed([query])[0]
        cutoff = (datetime.now(timezone.utc) - timedelta(days=time_range_days)).isoformat()
        result: dict[MemoryLevel, list[str]] = {}
        with httpx.Client(timeout=30.0) as client:
            for level in levels:
                filters: list[dict] = [
                    {"term": {"owner_hash": owner_hash}},
                    {"term": {"memory_level": level}},
                    {"range": {"last_seen_at": {"gte": cutoff}}},
                ]
                if knowledge_tags:
                    filters.append({"terms": {"knowledge_tags": list(knowledge_tags)}})
                lexical_query = {
                    "size": max(limits[level] * 4, 20),
                    "query": {
                        "bool": {
                            "filter": filters,
                            "must_not": [{"term": {"memory_status": "superseded"}}],
                            "must": [{"multi_match": {
                                "query": query,
                                "fields": ["summary^4", "title^3", "knowledge_tags^2", "error_type^2"],
                                "type": "best_fields",
                            }}],
                        }
                    },
                    "_source": ["memory_id"],
                }
                vector_query = {
                    "size": max(limits[level] * 4, 20),
                    "knn": {
                        "field": "content_vector",
                        "query_vector": vector,
                        "k": max(limits[level] * 4, 20),
                        "num_candidates": max(100, limits[level] * 20),
                        "filter": {"bool": {
                            "filter": filters,
                            "must_not": [{"term": {"memory_status": "superseded"}}],
                        }},
                    },
                    "_source": ["memory_id"],
                }
                lexical = client.post(f"{self.base_url}/{self.index_name}/_search", json=lexical_query)
                dense = client.post(f"{self.base_url}/{self.index_name}/_search", json=vector_query)
                lexical.raise_for_status()
                dense.raise_for_status()
                scores: dict[str, float] = {}
                for weight, response in ((1.0, lexical), (1.5, dense)):
                    for rank, hit in enumerate(response.json().get("hits", {}).get("hits", []), start=1):
                        memory_id = str((hit.get("_source") or {}).get("memory_id") or "")
                        if memory_id:
                            scores[memory_id] = scores.get(memory_id, 0.0) + weight / (60 + rank)
                ranked = sorted(
                    (item for item in scores.items() if item[1] >= self.min_rrf_score),
                    key=lambda item: (-item[1], item[0]),
                )
                result[level] = [memory_id for memory_id, _score in ranked[:limits[level]]]
        return result


def owner_hash(secret: str, user_id: str) -> str:
    return sha256(f"{secret}\0{user_id}".encode()).hexdigest()
