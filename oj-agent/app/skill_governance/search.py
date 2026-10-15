from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
import re
from threading import Lock
from typing import Any, Iterable

import httpx


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PROFILE_RE = re.compile(r"\bsyncode-u\d+\b", re.IGNORECASE)
_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret|authorization)\b\s*[:=]\s*[^\s,;]+"
)
_HOME_RE = re.compile(r"(?:/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:\\Users\\[^\\\s]+)")
_LONG_NUMBER_RE = re.compile(r"\b\d{7,}\b")


def redact_for_shared_index(value: str, *, limit: int = 24_000) -> str:
    text = value[:limit]
    text = _EMAIL_RE.sub("[email]", text)
    text = _PROFILE_RE.sub("[profile]", text)
    text = _SECRET_RE.sub(lambda match: f"{match.group(1)}=[redacted]", text)
    text = _HOME_RE.sub("[home]", text)
    text = _LONG_NUMBER_RE.sub("[number]", text)
    return text


class SkillSearchError(RuntimeError):
    pass


class EmbeddingClient:
    _local_models: dict[tuple[str, str, str], Any] = {}
    _local_models_lock = Lock()

    def __init__(self) -> None:
        self.url = (os.getenv("SYNCODE_SKILL_EMBEDDING_URL") or "").strip()
        self.api_key = (os.getenv("SYNCODE_SKILL_EMBEDDING_API_KEY") or "").strip()
        self.model = (os.getenv("SYNCODE_SKILL_EMBEDDING_MODEL") or "").strip()
        self.dimensions = int(os.getenv("SYNCODE_SKILL_EMBEDDING_DIMENSIONS", "1024"))

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.model and self.dimensions > 0)

    @property
    def local(self) -> bool:
        return self.url == "local://fastembed"

    def _local_model(self):
        cache_dir = os.getenv("FASTEMBED_CACHE_PATH", "/opt/fastembed-cache")
        model_path = os.getenv("FASTEMBED_MODEL_PATH", "/opt/fastembed-model")
        key = (self.model, cache_dir, model_path)
        with self._local_models_lock:
            model = self._local_models.get(key)
            if model is None:
                try:
                    from fastembed import TextEmbedding
                except ImportError as exc:
                    raise SkillSearchError("Local embedding runtime is unavailable.") from exc
                threads = max(1, int(os.getenv("SYNCODE_SKILL_EMBEDDING_THREADS", "2")))
                model = TextEmbedding(
                    model_name=self.model,
                    cache_dir=cache_dir,
                    threads=threads,
                    local_files_only=True,
                    specific_model_path=model_path,
                )
                self._local_models[key] = model
            return model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.enabled:
            raise SkillSearchError("Skill embedding service is not configured.")
        if self.local:
            try:
                vectors = [vector.tolist() for vector in self._local_model().embed(texts)]
            except SkillSearchError:
                raise
            except Exception as exc:
                raise SkillSearchError("Local embedding generation failed.") from exc
        else:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.url,
                    headers=headers,
                    json={"model": self.model, "input": texts, "dimensions": self.dimensions},
                )
                response.raise_for_status()
                payload = response.json()
            rows = sorted(payload.get("data") or [], key=lambda item: int(item.get("index", 0)))
            vectors = [item.get("embedding") for item in rows]
        if len(vectors) != len(texts) or any(not isinstance(vector, list) for vector in vectors):
            raise SkillSearchError("Embedding service returned an invalid response.")
        if any(len(vector) != self.dimensions for vector in vectors):
            raise SkillSearchError("Embedding dimensions do not match the configured index.")
        return vectors


@dataclass(frozen=True)
class IndexedSkill:
    skill_id: str
    version: str
    owner_hash: str
    name: str
    description: str
    category: str | None
    content: str
    content_hash: str

    @property
    def document_id(self) -> str:
        return sha256(f"{self.skill_id}\0{self.version}".encode()).hexdigest()

    @property
    def embedding_text(self) -> str:
        return "\n".join(part for part in (self.description, self.category or "", self.content) if part)


class ElasticsearchSkillIndex:
    """Private hybrid index containing de-identified personal Skill fingerprints."""

    def __init__(self, embedder: EmbeddingClient | None = None) -> None:
        self.base_url = (
            os.getenv("SYNCODE_ELASTICSEARCH_URL")
            or os.getenv("SPRING_ELASTICSEARCH_URIS")
            or ""
        ).strip().rstrip("/")
        self.index_name = os.getenv("SYNCODE_SKILL_INDEX", "syncode-personal-skills-v1").strip()
        self.embedder = embedder or EmbeddingClient()
        self.min_rrf_score = float(os.getenv("SYNCODE_SKILL_MIN_RRF_SCORE", "0.03"))
        self._replace_lock = Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.embedder.enabled)

    def ensure_index(self) -> None:
        if not self.enabled:
            raise SkillSearchError("Hybrid Skill indexing is not fully configured.")
        mapping = {
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "skill_id": {"type": "keyword"},
                    "version": {"type": "keyword"},
                    "owner_hash": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "description": {"type": "text"},
                    "category": {"type": "keyword"},
                    "content": {"type": "text"},
                    "content_hash": {"type": "keyword"},
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

    def upsert(self, rows: Iterable[IndexedSkill]) -> int:
        skills = list(rows)
        if not skills:
            return 0
        with self._replace_lock:
            self.ensure_index()
            return self._upsert(skills)

    def replace_owner(self, owner_hash: str, rows: Iterable[IndexedSkill]) -> int:
        skills = list(rows)
        with self._replace_lock:
            self.ensure_index()
            self._delete_by_query({"term": {"owner_hash": owner_hash}})
            return self._upsert(skills)

    def replace_all(self, rows: Iterable[IndexedSkill]) -> int:
        skills = list(rows)
        with self._replace_lock:
            self.ensure_index()
            self._delete_by_query({"match_all": {}})
            return self._upsert(skills)

    def _delete_by_query(self, query: dict) -> None:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/{self.index_name}/_delete_by_query?refresh=true&conflicts=proceed",
                json={"query": query},
            )
            response.raise_for_status()

    def _upsert(self, skills: list[IndexedSkill]) -> int:
        if not skills:
            return 0
        vectors = self.embedder.embed([skill.embedding_text for skill in skills])
        lines: list[str] = []
        import json

        for skill, vector in zip(skills, vectors, strict=True):
            lines.append(json.dumps({"index": {"_index": self.index_name, "_id": skill.document_id}}))
            lines.append(json.dumps({
                "skill_id": skill.skill_id,
                "version": skill.version,
                "owner_hash": skill.owner_hash,
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "content": skill.content,
                "content_hash": skill.content_hash,
                "content_vector": vector,
            }, ensure_ascii=False))
        body = "\n".join(lines) + "\n"
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/_bulk?refresh=true",
                headers={"Content-Type": "application/x-ndjson"},
                content=body.encode("utf-8"),
            )
            response.raise_for_status()
            payload = response.json()
        if payload.get("errors"):
            raise SkillSearchError("Elasticsearch rejected one or more Skill documents.")
        return len(skills)

    def neighbors(self, skill: IndexedSkill, *, limit: int = 20) -> list[tuple[str, float]]:
        self.ensure_index()
        vector = self.embedder.embed([skill.embedding_text])[0]
        exclusion = [
            {"term": {"owner_hash": skill.owner_hash}},
            {"term": {"content_hash": skill.content_hash}},
        ]
        lexical_query = {
            "size": limit,
            "query": {
                "bool": {
                    "must": [{
                        "multi_match": {
                            "query": skill.embedding_text,
                            "fields": ["description^4", "content^2", "category"],
                            "type": "best_fields",
                        }
                    }],
                    "must_not": exclusion,
                }
            },
            "_source": ["skill_id"],
        }
        vector_query = {
            "size": limit,
            "knn": {
                "field": "content_vector",
                "query_vector": vector,
                "k": limit,
                "num_candidates": max(100, limit * 5),
                "filter": {"bool": {"must_not": exclusion}},
            },
            "_source": ["skill_id"],
        }
        with httpx.Client(timeout=30.0) as client:
            lexical = client.post(f"{self.base_url}/{self.index_name}/_search", json=lexical_query)
            dense = client.post(f"{self.base_url}/{self.index_name}/_search", json=vector_query)
            lexical.raise_for_status()
            dense.raise_for_status()
        scores: dict[str, float] = {}
        for weight, response in ((1.0, lexical), (1.5, dense)):
            hits = response.json().get("hits", {}).get("hits", [])
            for rank, hit in enumerate(hits, start=1):
                skill_id = str((hit.get("_source") or {}).get("skill_id") or "")
                if skill_id:
                    scores[skill_id] = scores.get(skill_id, 0.0) + weight / (60 + rank)
        ranked = sorted(
            (item for item in scores.items() if item[1] >= self.min_rrf_score),
            key=lambda item: (-item[1], item[0]),
        )
        return ranked[:limit]
