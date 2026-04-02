from copy import deepcopy
from threading import Lock

from app.domain.artifacts import Artifact


class ArtifactStore:
    """In-memory artifact repository keyed by run id."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._artifacts: dict[str, list[Artifact]] = {}

    def append(self, artifact: Artifact) -> Artifact:
        with self._lock:
            self._artifacts.setdefault(artifact.run_id, []).append(artifact)
            return deepcopy(artifact)

    def list_for_run(self, run_id: str) -> list[Artifact]:
        with self._lock:
            return [deepcopy(item) for item in self._artifacts.get(run_id, [])]

    def clear(self) -> None:
        with self._lock:
            self._artifacts.clear()

