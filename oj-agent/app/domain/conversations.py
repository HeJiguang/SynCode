from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConversationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ROLLED_OVER = "ROLLED_OVER"
    ARCHIVED = "ARCHIVED"


class MessageRole(str, Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class MessageStatus(str, Enum):
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class MemoryStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Conversation(BaseModel):
    conversation_id: str
    user_id: str
    title: str
    status: ConversationStatus
    is_default: bool = False
    current_question_id: str | None = None
    current_question_title: str | None = None
    continued_from_conversation_id: str | None = None
    message_count: int = 0
    context_token_estimate: int = 0
    soft_token_limit: int
    hard_token_limit: int
    created_at: str
    updated_at: str
    last_message_at: str | None = None

    @property
    def rollover_recommended(self) -> bool:
        return self.context_token_estimate >= self.soft_token_limit

    @property
    def hard_limit_reached(self) -> bool:
        return self.context_token_estimate >= self.hard_token_limit


class ConversationMessage(BaseModel):
    message_id: str
    conversation_id: str
    run_id: str | None = None
    role: MessageRole
    content: str
    sequence: int
    question_id: str | None = None
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    artifact: dict[str, Any] | None = None
    token_estimate: int = 0
    status: MessageStatus = MessageStatus.COMPLETE
    created_at: str


class MemoryItem(BaseModel):
    memory_id: str
    user_id: str
    memory_type: str
    content: str
    reason: str | None = None
    confidence: float = 0.0
    status: MemoryStatus = MemoryStatus.PENDING
    source_conversation_id: str | None = None
    source_message_id: str | None = None
    created_at: str
    reviewed_at: str | None = None


class ConversationSnapshot(BaseModel):
    conversation: Conversation
    messages: list[ConversationMessage] = Field(default_factory=list)
    context_memories: list[MemoryItem] = Field(default_factory=list)

