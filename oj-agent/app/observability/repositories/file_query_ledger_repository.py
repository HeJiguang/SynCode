from pathlib import Path

from app.core.jsonl_store import append_jsonl, clear_jsonl, read_jsonl
from app.observability.query_ledger import QueryLedgerEntry


class JsonlQueryLedgerRepository:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.path = self.base_dir / "query-ledger.jsonl"

    def append(self, entry: QueryLedgerEntry) -> None:
        append_jsonl(self.path, entry.model_dump(mode="json"))

    def list_entries(self) -> list[QueryLedgerEntry]:
        return [QueryLedgerEntry.model_validate(row) for row in read_jsonl(self.path)]

    def clear(self) -> None:
        clear_jsonl(self.path)
