from copy import deepcopy
from threading import Lock

from app.domain.inbox import InboxItem, InboxItemStatus
from app.domain.runs import utc_now_iso


class InboxStore:
    """In-memory inbox repository for asynchronous user-facing items."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._items: dict[str, list[InboxItem]] = {}

    def append(self, item: InboxItem) -> InboxItem:
        with self._lock:
            self._items.setdefault(item.user_id, []).append(item)
            return deepcopy(item)

    def list_for_user(self, user_id: str) -> list[InboxItem]:
        with self._lock:
            return [deepcopy(item) for item in self._items.get(user_id, [])]

    def resolve_by_draft(self, draft_id: str) -> None:
        with self._lock:
            for user_id, items in self._items.items():
                updated_items = []
                for item in items:
                    if item.linked_draft_id == draft_id:
                        updated_items.append(
                            item.model_copy(
                                update={
                                    "status": InboxItemStatus.RESOLVED,
                                    "updated_at": utc_now_iso(),
                                }
                            )
                        )
                    else:
                        updated_items.append(item)
                self._items[user_id] = updated_items

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
