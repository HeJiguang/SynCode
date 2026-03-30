from pathlib import Path

from app.evaluation.store import InMemoryEvaluationStore


def test_evaluation_store_can_use_custom_repository():
    class _StubEvaluationRepository:
        def __init__(self):
            self.records = []

        def append(self, record):
            self.records.append(record)

        def list_records(self):
            return list(self.records)

        def clear(self):
            self.records.clear()

    repository = _StubEvaluationRepository()
    store = InMemoryEvaluationStore(repository=repository)
    store.append({"trace_id": "trace-eval-store-001", "task_type": "chat"})

    assert repository.list_records()[0]["trace_id"] == "trace-eval-store-001"


def test_jsonl_evaluation_repository_persists_records(tmp_path):
    from app.evaluation.repositories.file_evaluation_repository import JsonlEvaluationRepository  # noqa: WPS433

    repository = JsonlEvaluationRepository(tmp_path)
    repository.append({"trace_id": "trace-eval-file-001", "task_type": "review"})

    assert repository.list_records()[0]["task_type"] == "review"
    assert (tmp_path / "evaluation-records.jsonl").exists()


def test_build_default_evaluation_store_can_use_file_repository(monkeypatch, tmp_path):
    import app.evaluation.store as store_module  # noqa: WPS433

    monkeypatch.setenv("OJ_AGENT_EVALUATION_STORE", "file")
    monkeypatch.setenv("OJ_AGENT_RUNTIME_DATA_DIR", str(tmp_path))

    store = store_module.build_default_evaluation_store()
    store.append({"trace_id": "trace-eval-file-002", "task_type": "chat"})

    assert store.list_records()[0]["trace_id"] == "trace-eval-file-002"
    assert (Path(tmp_path) / "evaluation-records.jsonl").exists()
