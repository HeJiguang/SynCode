from app.agent_runtime.base import AgentRunRequest, AgentRunResult, AgentRuntime, AgentRuntimeError
from app.llm.base import LLMClient


class DirectAgentRuntime(AgentRuntime):
    """Adapter for the existing OpenAI-compatible DeepSeek client."""

    def __init__(self, client: LLMClient, *, provider: str = "openai_compatible") -> None:
        self.client = client
        self.provider = provider

    @property
    def name(self) -> str:
        return "direct"

    def is_available(self) -> bool:
        return self.client.is_available()

    def model_name(self, capability: str) -> str:
        return self.client.model_name(capability)

    def generate(self, request: AgentRunRequest) -> AgentRunResult:
        try:
            text = self.client.generate_text(
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                capability=request.capability,
            )
        except Exception as exc:
            raise AgentRuntimeError(f"Direct Agent Runtime 调用失败：{exc}") from exc
        if not text.strip():
            raise AgentRuntimeError("Direct Agent Runtime 没有返回有效内容。")
        return AgentRunResult(
            text=text,
            runtime_name=self.name,
            provider=self.provider,
            model_name=self.model_name(request.capability),
        )
