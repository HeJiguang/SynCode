from app.core.config import load_settings
from app.llm.base import LLMClient
from app.llm.openai_compatible import OpenAICompatibleLLMClient


def build_llm_client() -> LLMClient:
    settings = load_settings()
    if not settings.llm_enabled:
        raise RuntimeError(
            "未配置可用的大模型，请先设置 OJ_AGENT_LLM_BASE_URL、OJ_AGENT_LLM_API_KEY、"
            "OJ_AGENT_CHAT_MODEL 和 OJ_AGENT_TRAINING_MODEL。"
        )

    if settings.llm_provider != "openai_compatible":
        raise RuntimeError(f"暂不支持的大模型提供方: {settings.llm_provider}")

    client = OpenAICompatibleLLMClient(settings)
    if not client.is_available():
        raise RuntimeError("当前大模型配置不可用，请检查模型名称、API Key 和服务地址。")
    return client
