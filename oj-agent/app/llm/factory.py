from app.core.config import load_settings
from app.llm.base import LLMClient
from app.llm.fallback import UnavailableLLMClient
from app.llm.openai_compatible import OpenAICompatibleLLMClient


def build_llm_client() -> LLMClient:
    """
    构建并返回大语言模型客户端实例 (Factory Function)
    
    这是一个典型的“简单工厂模式”。它的作用是根据系统的配置环境，
    动态决定实例化哪一个具体的 LLMClient 子类（实现类），
    并对外隐藏具体的实例化细节。
    """
    # 1. 加载系统配置（通常是从环境变量、YAML 或 .env 文件中读取）
    settings = load_settings()
    
    # 2. 优雅降级 (Graceful Degradation) / 空对象模式 (Null Object Pattern)
    # 如果系统配置中明确禁用了 LLM 功能（比如在跑单元测试，或者 API 额度耗尽紧急关停时）：
    # 我们不返回 None（返回 None 会导致调用方到处报 AttributeError/空指针异常），
    # 而是返回一个专门的 UnavailableLLMClient（它实现了 LLMClient 的接口，但调用时可能会安全地返回空值或抛出受控的自定义异常）。
    if not settings.llm_enabled:
        return UnavailableLLMClient("llm is disabled")
    
    # 3. 根据配置的提供商 (Provider) 动态路由
    # "openai_compatible" 是一种非常聪明的做法。现在的开源模型（如 Llama, Qwen）部署工具（如 vLLM, Ollama）
    # 通常都会提供与 OpenAI 完全兼容的 API 接口。
    # 这样一套代码既能调官方 ChatGPT，也能调本地私有化部署的模型。
    if settings.llm_provider == "openai_compatible":
        # 实例化并返回真正干活的客户端，并将配置信息（如 API Key, Base URL 等）传给它
        return OpenAICompatibleLLMClient(settings)
    
    # 4. 容错底线处理
    # 如果用户在配置文件里填了一个系统目前不支持的供应商（比如 "anthropic" 但代码还没实现）：
    # 同样返回一个 UnavailableLLMClient，并把错误信息带进去，方便开发者在日志中一眼看出配置写错了。
    return UnavailableLLMClient(f"unsupported llm provider: {settings.llm_provider}")