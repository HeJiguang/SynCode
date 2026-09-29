from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
from typing import Any


class AgentRuntimeError(RuntimeError):
    """A runtime failed before it could return a usable agent response."""


@dataclass(frozen=True)
class AgentRunRequest:
    system_prompt: str
    user_prompt: str
    capability: str
    user_id: str
    trace_id: str
    conversation_id: str | None = None


@dataclass(frozen=True)
class AgentRunResult:
    text: str
    runtime_name: str
    provider: str
    model_name: str
    session_id: str | None = None
    remote_run_id: str | None = None
    fallback_from: str | None = None
    tool_decisions: tuple[dict[str, Any], ...] = field(default_factory=tuple)


class AgentRuntime(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def model_name(self, capability: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: AgentRunRequest) -> AgentRunResult:
        raise NotImplementedError

    def generate_json(self, request: AgentRunRequest) -> tuple[AgentRunResult, dict[str, Any]]:
        result = self.generate(request)
        return result, extract_json_object(result.text)


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise AgentRuntimeError("智能体响应中没有可解析的 JSON 对象。")

    try:
        payload = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AgentRuntimeError("智能体返回了无效的 JSON。") from exc
    if not isinstance(payload, dict):
        raise AgentRuntimeError("智能体响应必须是 JSON 对象。")
    return payload
