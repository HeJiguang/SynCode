from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _CamelCaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_camel_case(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        key_map = {
            "runType": "run_type",
            "userId": "user_id",
            "conversationId": "conversation_id",
            "questionId": "question_id",
            "questionTitle": "question_title",
            "questionContent": "question_content",
            "userCode": "user_code",
            "judgeResult": "judge_result",
            "submissionId": "submission_id",
            "userMessage": "user_message",
        }
        for source_key, target_key in key_map.items():
            if source_key in normalized and target_key not in normalized:
                normalized[target_key] = normalized[source_key]
        return normalized


class RunContextPayload(_CamelCaseModel):
    question_id: str | None = Field(default=None)
    question_title: str | None = Field(default=None)
    question_content: str | None = Field(default=None)
    user_code: str | None = Field(default=None)
    judge_result: str | None = Field(default=None)
    submission_id: str | None = Field(default=None)
    user_message: str | None = Field(default=None)


# 创建run的请求体
class CreateRunRequest(_CamelCaseModel):
    run_type: str
    source: str
    user_id: str | None = Field(default=None)
    conversation_id: str | None = Field(default=None)
    context: RunContextPayload = Field(default_factory=RunContextPayload)


class DraftActionRequest(_CamelCaseModel):
    user_id: str
