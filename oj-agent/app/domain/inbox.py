from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.runs import utc_now_iso


class InboxItemType(str, Enum):
    DRAFT_REVIEW = "draft_review"
    PROFILE_UPDATE = "profile_update"
    PLAN_RECOMPUTE = "plan_recompute"
    WEAKNESS_TRACKING = "weakness_tracking"
    MESSAGE = "message"


class InboxItemStatus(str, Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    RESOLVED = "RESOLVED"


class InboxItem(BaseModel):
    inbox_item_id: str = Field(default_factory=lambda: f"inbox_{uuid4().hex}")
    user_id: str
    run_id: str
    item_type: InboxItemType
    title: str
    summary: str
    status: InboxItemStatus = InboxItemStatus.UNREAD
    linked_draft_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

