from pathlib import Path

from app.core.jsonl_store import append_jsonl, clear_jsonl, read_jsonl


class JsonlEvaluationRepository:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.path = self.base_dir / "evaluation-records.jsonl"

    def append(self, record: dict) -> None:
        append_jsonl(self.path, dict(record))

    def list_records(self) -> list[dict]:
        return read_jsonl(self.path)

    def clear(self) -> None:
        clear_jsonl(self.path)
