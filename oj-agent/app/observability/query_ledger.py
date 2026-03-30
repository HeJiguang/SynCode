from pydantic import BaseModel, Field


class QueryLedgerEntry(BaseModel):
    trace_id: str
    run_id: str
    user_id: str
    task_type: str
    request_text: str
    graph_path: list[str] = Field(default_factory=list)
    route_names: list[str] = Field(default_factory=list)
    evidence_sources: list[str] = Field(default_factory=list)
    output_type: str
    risk_level: str = "low"
    token_cost: int = 0
    latency_ms: int = 0


class QueryLedger:
    def __init__(self, repository=None) -> None:
        self._repository = repository or self
        self._entries: list[QueryLedgerEntry] = []

    def append(self, entry: QueryLedgerEntry) -> None:
        if self._repository is not self:
            self._repository.append(entry)
            return
        self._entries.append(entry)

    def list_entries(self) -> list[QueryLedgerEntry]:
        if self._repository is not self:
            return self._repository.list_entries()
        return list(self._entries)

    def clear(self) -> None:
        if self._repository is not self:
            self._repository.clear()
            return
        self._entries.clear()


def build_default_query_ledger() -> QueryLedger:
    from pathlib import Path

    from app.core.config import load_settings
    from app.observability.repositories.file_query_ledger_repository import JsonlQueryLedgerRepository

    settings = load_settings()
    if settings.query_ledger_store_backend.strip().lower() == "file":
        return QueryLedger(repository=JsonlQueryLedgerRepository(Path(settings.runtime_data_dir)))
    return QueryLedger()


query_ledger = build_default_query_ledger()
