from collections.abc import Iterator
from typing import Any

from app.llm.base import LLMClient


class UnavailableLLMClient(LLMClient):
    """
    不可用状态的大语言模型客户端 (UnavailableLLMClient)
    
    当系统配置禁用 LLM 或出现不支持的提供商时实例化此类。
    它确保了系统架构的统一性（符合 LLMClient 接口契约），
    同时通过阻断非法调用来保护系统运行时的稳定性。
    """
    
    def __init__(self, reason: str = "llm unavailable") -> None:
        """
        初始化时接收一个 reason（原因），例如 "llm is disabled"。
        将原因保存下来，是为了在错误发生时提供精准的排查线索。
        """
        self._reason = reason

    def is_available(self) -> bool:
        """
        向外界明确声明当前服务不可用。
        优雅降级策略：业务层在调用 AI 前，通常会写 `if client.is_available():`。
        如果这里返回 False，业务层就可以主动切换到传统的“死代码”规则引擎（即降级方案），
        从而避免触发后续的报错。
        """
        return False

    def model_name(self, capability: str) -> str:
        """
        返回占位模型名称："heuristic-fallback"（启发式/规则回退）。
        核心细节：当数据分析师或运维查看系统日志时，看到这个名字就能立刻明白：
        “哦，这次请求并没有消耗真实大模型的 Token，而是走了系统后备的默认规则。”
        """
        return "heuristic-fallback"

    def generate_text(self, *, system_prompt: str, user_prompt: str, capability: str) -> str:
        """
        快速失败 (Fail-Fast) 机制的体现。
        如果上层业务逻辑忘记检查 `is_available()`，强行调用了生成接口，
        这里绝对不能默默返回一个空字符串 `""`（这会导致下游逻辑出现极其隐蔽的 Bug）。
        而是要立刻抛出包含具体原因的 RuntimeError，让程序“死得明明白白”。
        """
        raise RuntimeError(self._reason)

    def stream_text(self, *, system_prompt: str, user_prompt: str, capability: str) -> Iterator[str]:
        """
        拦截非法的流式输出请求并抛出异常。
        """
        raise RuntimeError(self._reason)

    def generate_json(self, *, system_prompt: str, user_prompt: str, capability: str) -> dict[str, Any]:
        """
        拦截非法的结构化 JSON 生成请求并抛出异常。
        这能有效防止下游的 JSON 解析库（如 json.loads）因为收到无效数据而崩溃。
        """
        raise RuntimeError(self._reason)