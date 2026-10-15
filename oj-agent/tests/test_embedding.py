from __future__ import annotations

import sys
from types import SimpleNamespace

from app.skill_governance.search import EmbeddingClient


class _Vector:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values


def test_local_fastembed_generates_configured_vectors(monkeypatch, tmp_path):
    created: list[tuple[str, str, int]] = []

    class FakeTextEmbedding:
        def __init__(self, *, model_name: str, cache_dir: str, threads: int) -> None:
            created.append((model_name, cache_dir, threads))

        def embed(self, texts: list[str]):
            return [_Vector([float(index), 1.0, 2.0]) for index, _ in enumerate(texts)]

    monkeypatch.setitem(sys.modules, "fastembed", SimpleNamespace(TextEmbedding=FakeTextEmbedding))
    monkeypatch.setenv("SYNCODE_SKILL_EMBEDDING_URL", "local://fastembed")
    monkeypatch.setenv("SYNCODE_SKILL_EMBEDDING_MODEL", "test-zh-model")
    monkeypatch.setenv("SYNCODE_SKILL_EMBEDDING_DIMENSIONS", "3")
    monkeypatch.setenv("SYNCODE_SKILL_EMBEDDING_THREADS", "1")
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path / "models"))
    EmbeddingClient._local_models.clear()

    client = EmbeddingClient()
    assert client.local is True
    assert client.embed(["边界错误", "复习计划"]) == [
        [0.0, 1.0, 2.0],
        [1.0, 1.0, 2.0],
    ]
    assert created == [("test-zh-model", str(tmp_path / "models"), 1)]

