from copy import deepcopy
from threading import Lock

from app.domain.drafts import Draft, DraftStatus
from app.domain.runs import utc_now_iso


class DraftStore:
    """In-memory draft repository for human review flows."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._drafts: dict[str, Draft] = {}

    def save(self, draft: Draft) -> Draft:
        with self._lock:
            self._drafts[draft.draft_id] = draft
            return deepcopy(draft)

    def get(self, draft_id: str) -> Draft:
        with self._lock:
            return deepcopy(self._drafts[draft_id])

    def list_for_user(self, user_id: str) -> list[Draft]:
        with self._lock:
            return [deepcopy(item) for item in self._drafts.values() if item.user_id == user_id]

    def update_status(self, draft_id: str, status: DraftStatus) -> Draft:
        with self._lock:
            draft = self._drafts[draft_id]
            updated = draft.model_copy(
                update={
                    "status": status,
                    "resolved_at": utc_now_iso() if status in {DraftStatus.APPROVED, DraftStatus.REJECTED, DraftStatus.APPLIED} else draft.resolved_at,
                }
            )
            self._drafts[draft_id] = updated
            return deepcopy(updated)

    def clear(self) -> None:
        with self._lock:
            self._drafts.clear()
