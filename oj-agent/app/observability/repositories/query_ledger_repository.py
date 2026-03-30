from typing import Protocol

from app.observability.query_ledger import QueryLedgerEntry


class QueryLedgerRepository(Protocol):
    def append(self, entry: QueryLedgerEntry) -> None: ...

    def list_entries(self) -> list[QueryLedgerEntry]: ...

    def clear(self) -> None: ...
