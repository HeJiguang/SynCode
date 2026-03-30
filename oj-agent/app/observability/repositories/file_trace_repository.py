from pathlib import Path

from app.core.jsonl_store import append_jsonl, clear_jsonl, read_jsonl
from app.observability.trace import NodeTraceEvent, RunTrace


class JsonlTraceRepository:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.run_path = self.base_dir / "trace-runs.jsonl"
        self.node_event_path = self.base_dir / "trace-node-events.jsonl"

    def record_run(self, run_trace: RunTrace) -> None:
        append_jsonl(self.run_path, run_trace.model_dump(mode="json"))

    def record_node_event(self, event: NodeTraceEvent) -> None:
        append_jsonl(self.node_event_path, event.model_dump(mode="json"))

    def get_run(self, run_id: str) -> RunTrace:
        for row in reversed(read_jsonl(self.run_path)):
            if row.get("run_id") == run_id:
                return RunTrace.model_validate(row)
        raise KeyError(run_id)

    def list_node_events(self, run_id: str) -> list[NodeTraceEvent]:
        return [
            NodeTraceEvent.model_validate(row)
            for row in read_jsonl(self.node_event_path)
            if row.get("run_id") == run_id
        ]

    def clear(self) -> None:
        clear_jsonl(self.run_path)
        clear_jsonl(self.node_event_path)
