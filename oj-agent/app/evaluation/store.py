class InMemoryEvaluationStore:
    def __init__(self, repository=None) -> None:
        self._repository = repository or self
        self._records: list[dict] = []

    def append(self, record: dict) -> None:
        if self._repository is not self:
            self._repository.append(record)
            return
        self._records.append(record)

    def list_records(self) -> list[dict]:
        if self._repository is not self:
            return self._repository.list_records()
        return list(self._records)

    def clear(self) -> None:
        if self._repository is not self:
            self._repository.clear()
            return
        self._records.clear()


def build_default_evaluation_store() -> InMemoryEvaluationStore:
    from pathlib import Path

    from app.core.config import load_settings
    from app.evaluation.repositories.file_evaluation_repository import JsonlEvaluationRepository

    settings = load_settings()
    if settings.evaluation_store_backend.strip().lower() == "file":
        return InMemoryEvaluationStore(repository=JsonlEvaluationRepository(Path(settings.runtime_data_dir)))
    return InMemoryEvaluationStore()


evaluation_store = build_default_evaluation_store()
