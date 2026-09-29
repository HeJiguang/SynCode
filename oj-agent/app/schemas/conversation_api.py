from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CreateConversationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(default="新的学习对话", max_length=160)
    continued_from_conversation_id: str | None = None
    memory_ids: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="before")
    @classmethod
    def normalize_camel_case(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        for source, target in {
            "continuedFromConversationId": "continued_from_conversation_id",
            "memoryIds": "memory_ids",
        }.items():
            if source in normalized and target not in normalized:
                normalized[target] = normalized[source]
        return normalized

