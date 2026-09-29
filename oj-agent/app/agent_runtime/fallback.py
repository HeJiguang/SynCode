from dataclasses import replace
from typing import Any

from app.agent_runtime.base import AgentRunRequest, AgentRunResult, AgentRuntime, AgentRuntimeError


class FallbackAgentRuntime(AgentRuntime):
    """Run a secondary runtime when the primary cannot produce a usable result."""

    def __init__(self, primary: AgentRuntime, fallback: AgentRuntime) -> None:
        self.primary = primary
        self.fallback = fallback

    @property
    def name(self) -> str:
        return self.primary.name

    def is_available(self) -> bool:
        return self.primary.is_available() or self.fallback.is_available()

    def model_name(self, capability: str) -> str:
        if self.primary.is_available():
            return self.primary.model_name(capability)
        return self.fallback.model_name(capability)

    def generate(self, request: AgentRunRequest) -> AgentRunResult:
        try:
            return self.primary.generate(request)
        except AgentRuntimeError:
            return self._fallback_result(self.fallback.generate(request))

    def generate_json(self, request: AgentRunRequest) -> tuple[AgentRunResult, dict[str, Any]]:
        try:
            return self.primary.generate_json(request)
        except AgentRuntimeError:
            result, payload = self.fallback.generate_json(request)
            return self._fallback_result(result), payload

    def _fallback_result(self, result: AgentRunResult) -> AgentRunResult:
        return replace(result, fallback_from=self.primary.name)
