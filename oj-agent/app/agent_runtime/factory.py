from app.agent_runtime.base import AgentRuntime
from app.agent_runtime.direct import DirectAgentRuntime
from app.agent_runtime.fallback import FallbackAgentRuntime
from app.agent_runtime.hermes import HermesAgentRuntime
from app.core.config import AgentSettings, load_settings
from app.llm.openai_compatible import OpenAICompatibleLLMClient


def build_agent_runtime(settings: AgentSettings | None = None) -> AgentRuntime:
    settings = settings or load_settings()
    provider = settings.agent_runtime_provider.strip().lower()

    direct = DirectAgentRuntime(
        OpenAICompatibleLLMClient(settings),
        provider=settings.llm_provider,
    )
    if provider == "direct":
        if not direct.is_available():
            raise RuntimeError(
                "Direct Agent Runtime 配置不完整，请设置 OJ_AGENT_LLM_API_KEY 和模型名称。"
            )
        return direct

    if provider != "hermes":
        raise RuntimeError(f"不支持的 Agent Runtime: {settings.agent_runtime_provider}")

    hermes = HermesAgentRuntime(settings)
    if not hermes.is_available():
        raise RuntimeError(
            "Hermes Agent Runtime 配置不完整，请设置 OJ_AGENT_HERMES_BASE_URL、"
            "OJ_AGENT_HERMES_API_KEY 和模型名称。"
        )
    if settings.agent_runtime_fallback_to_direct and direct.is_available():
        return FallbackAgentRuntime(hermes, direct)
    return hermes
