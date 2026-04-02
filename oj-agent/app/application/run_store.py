from copy import deepcopy
from threading import Lock

from app.domain.runs import EventType, Run, RunEvent, RunStatus, utc_now_iso


class RunStore:
    """In-memory run repository for the learning-first runtime increment."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: dict[str, Run] = {}
        self._events: dict[str, list[RunEvent]] = {}

    def save(self, run: Run) -> Run:
        with self._lock:
            stored = run.model_copy(update={"updated_at": utc_now_iso()})
            self._runs[stored.run_id] = stored
            self._events.setdefault(stored.run_id, [])
            return stored

    def get(self, run_id: str) -> Run:
        with self._lock:
            return deepcopy(self._runs[run_id])

    def list_runs(self) -> list[Run]:
        with self._lock:
            return [deepcopy(item) for item in self._runs.values()]

    def append_event(self, run_id: str, event_type: EventType, payload: dict | None = None) -> RunEvent:
        with self._lock:
            seq = len(self._events.setdefault(run_id, [])) + 1
            event = RunEvent(
                run_id=run_id,
                seq=seq,
                event_type=event_type,
                payload=dict(payload or {}),
            )
            self._events[run_id].append(event)
            return deepcopy(event)

    def list_events(self, run_id: str) -> list[RunEvent]:
        with self._lock:
            return [deepcopy(item) for item in self._events.get(run_id, [])]

    def update_status(self, run_id: str, status: RunStatus, *, active_node: str | None = None) -> Run:
        with self._lock:
            run = self._runs[run_id]
            completed_at = utc_now_iso() if status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED} else run.completed_at
            updated = run.model_copy(
                update={
                    "status": status,
                    "active_node": active_node,
                    "updated_at": utc_now_iso(),
                    "completed_at": completed_at,
                }
            )
            self._runs[run_id] = updated
            return deepcopy(updated)

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()
            self._events.clear()

