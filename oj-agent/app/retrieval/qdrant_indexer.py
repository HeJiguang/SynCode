from dataclasses import dataclass
from hashlib import sha1
import math
from typing import Any

import httpx

from app.core.config import AgentSettings, load_settings
from app.retrieval.keyword_retriever import KnowledgeDocument, _load_documents


@dataclass(frozen=True)
class DenseChunk:
    point_id: int
    source: str
    title: str
    content: str
    snippet: str


class QdrantKnowledgeIndexer:
    def __init__(self, settings: AgentSettings | None = None) -> None:
        self.settings = settings or load_settings()
        self._indexed = False
        self._client: httpx.Client | None = None
        self._embedding_client = None

    def is_enabled(self) -> bool:
        if self.settings.embedding_provider == "local_hash":
            return bool(
                self.settings.qdrant_enabled
                and self.settings.qdrant_url
                and self.settings.embedding_dimensions > 0
            )
        return bool(
            self.settings.qdrant_enabled
            and self.settings.qdrant_url
            and self.settings.llm_base_url
            and self.settings.llm_api_key
            and self.settings.embedding_model
        )

    def ensure_index_ready(self) -> None:
        if not self.is_enabled() or self._indexed:
            return

        chunks = self._load_chunks()
        if not chunks:
            self._indexed = True
            return

        if self._collection_has_points():
            self._indexed = True
            return

        sample_vector = self.embed_text(chunks[0].content)
        self._ensure_collection(len(sample_vector))

        points = []
        for chunk in chunks:
            points.append(
                {
                    "id": chunk.point_id,
                    "vector": self.embed_text(chunk.content),
                    "payload": {
                        "source": chunk.source,
                        "title": chunk.title,
                        "snippet": chunk.snippet,
                    },
                }
            )

        self._request(
            "PUT",
            f"/collections/{self.settings.qdrant_collection}/points",
            params={"wait": "true"},
            json={"points": points},
        )
        self._indexed = True

    def embed_text(self, text: str) -> list[float]:
        if self.settings.embedding_provider == "local_hash":
            return _local_hash_embedding(text, self.settings.embedding_dimensions)
        client = self._embedding_client_instance()
        response = client.embeddings.create(
            model=self.settings.embedding_model,
            input=text,
        )
        return list(response.data[0].embedding)

    def search_by_vector(self, vector: list[float], limit: int) -> list[dict[str, Any]]:
        response = self._request(
            "POST",
            f"/collections/{self.settings.qdrant_collection}/points/search",
            json={
                "vector": vector,
                "limit": limit,
                "with_payload": True,
            },
        )
        payload = response.json()
        return list(payload.get("result") or [])

    def _load_chunks(self) -> list[DenseChunk]:
        docs = _load_documents(self.settings.rag_doc_globs)
        chunks: list[DenseChunk] = []
        for doc in docs:
            pieces = _chunk_document(doc, self.settings.qdrant_chunk_size, self.settings.rag_max_snippet_chars)
            chunks.extend(pieces)
        return chunks

    def _collection_has_points(self) -> bool:
        response = self._request(
            "GET",
            f"/collections/{self.settings.qdrant_collection}",
            allow_not_found=True,
        )
        if response.status_code == 404:
            return False

        payload = response.json()
        result = payload.get("result") or {}
        return int(result.get("points_count") or 0) > 0

    def _ensure_collection(self, vector_size: int) -> None:
        response = self._request(
            "GET",
            f"/collections/{self.settings.qdrant_collection}",
            allow_not_found=True,
        )
        if response.status_code != 404:
            return

        self._request(
            "PUT",
            f"/collections/{self.settings.qdrant_collection}",
            json={
                "vectors": {
                    "size": vector_size,
                    "distance": "Cosine",
                }
            },
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        allow_not_found: bool = False,
        **kwargs,
    ) -> httpx.Response:
        response = self._http_client().request(method, path, **kwargs)
        if allow_not_found and response.status_code == 404:
            return response
        response.raise_for_status()
        return response

    def _http_client(self) -> httpx.Client:
        if self._client is None:
            headers = {}
            if self.settings.qdrant_api_key:
                headers["api-key"] = self.settings.qdrant_api_key
            self._client = httpx.Client(
                base_url=self.settings.qdrant_url.rstrip("/"),
                headers=headers,
                timeout=20.0,
            )
        return self._client

    def _embedding_client_instance(self):
        if self._embedding_client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("openai package is not installed") from exc

            self._embedding_client = OpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
                timeout=self.settings.llm_timeout_seconds,
            )
        return self._embedding_client


def _local_hash_embedding(text: str, dimensions: int) -> list[float]:
    if dimensions <= 0:
        raise ValueError("embedding dimensions must be positive")

    values = [0.0] * dimensions
    normalized = text.strip().lower()
    if not normalized:
        return values

    for token in normalized.split():
        digest = sha1(token.encode("utf-8")).digest()
        for index, byte in enumerate(digest):
            slot = index % dimensions
            signed = (byte / 255.0) * 2.0 - 1.0
            values[slot] += signed

    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]


def _chunk_document(
    doc: KnowledgeDocument,
    chunk_size: int,
    snippet_size: int,
) -> list[DenseChunk]:
    normalized = " ".join(doc.content.split())
    if not normalized:
        return []

    size = max(chunk_size, 120)
    overlap = max(size // 5, 40)
    chunks: list[DenseChunk] = []
    start = 0
    chunk_index = 0

    while start < len(normalized):
        end = min(start + size, len(normalized))
        content = normalized[start:end].strip()
        if content:
            point_id = int(
                sha1(f"{doc.source}:{chunk_index}:{content}".encode("utf-8")).hexdigest()[:15],
                16,
            )
            chunks.append(
                DenseChunk(
                    point_id=point_id,
                    source=doc.source,
                    title=doc.title,
                    content=content,
                    snippet=content[:snippet_size],
                )
            )
            chunk_index += 1

        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)

    return chunks
