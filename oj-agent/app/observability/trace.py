from pydantic import BaseModel


class RunTrace(BaseModel):
    trace_id: str
    run_id: str
    graph_name: str
    task_type: str
    user_id: str


class NodeTraceEvent(BaseModel):
    trace_id: str
    run_id: str
    graph_name: str
    node_name: str
    status: str


class InMemoryTraceStore:
    def __init__(self, repository=None) -> None:
        self._repository = repository or self
        self._runs: dict[str, RunTrace] = {}
        self._node_events: dict[str, list[NodeTraceEvent]] = {}

    def record_run(self, run_trace: RunTrace) -> None:
        if self._repository is not self:
            self._repository.record_run(run_trace)
            return
        self._runs[run_trace.run_id] = run_trace

    def record_node_event(self, event: NodeTraceEvent) -> None:
        if self._repository is not self:
            self._repository.record_node_event(event)
            return
        self._node_events.setdefault(event.run_id, []).append(event)

    def get_run(self, run_id: str) -> RunTrace:
        if self._repository is not self:
            return self._repository.get_run(run_id)
        return self._runs[run_id]

    def list_node_events(self, run_id: str) -> list[NodeTraceEvent]:
        if self._repository is not self:
            return self._repository.list_node_events(run_id)
        return list(self._node_events.get(run_id, []))

    def clear(self) -> None:
        if self._repository is not self:
            self._repository.clear()
            return
        self._runs.clear()
        self._node_events.clear()


def build_default_trace_store() -> InMemoryTraceStore:
    from pathlib import Path

    from app.core.config import load_settings
    from app.observability.repositories.file_trace_repository import JsonlTraceRepository

    settings = load_settings()
    if settings.trace_store_backend.strip().lower() == "file":
        return InMemoryTraceStore(repository=JsonlTraceRepository(Path(settings.runtime_data_dir)))
    return InMemoryTraceStore()


trace_store = build_default_trace_store()
