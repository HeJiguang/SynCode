from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

# 定义模型能力的常量
# 核心细节：通过常量区分使用场景。
# 比如聊天场景可能用响应快的小模型，而生成训练计划（复杂的逻辑推理）可能用更强大的大模型。
CHAT_CAPABILITY = "chat"
TRAINING_CAPABILITY = "training"


class LLMClient(ABC):
    """
    大语言模型客户端抽象基类 (LLMClient)
    定义了与底层 AI 模型交互的标准接口。任何具体的模型客户端（如 OpenAIClient, GeminiClient）
    都必须继承此基类，并实现（Override）下面所有的 @abstractmethod 方法。
    """

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查当前 LLM 服务是否可用。
        通常用于健康检查 (Health Check)，比如检查 API Key 是否有效、服务是否宕机、网络是否连通等。
        
        Raises:
            NotImplementedError: 如果子类没有实现这个方法，调用时就会报错。
        """
        raise NotImplementedError

    @abstractmethod
    def model_name(self, capability: str) -> str:
        """
        根据不同的能力需求（capability）返回实际使用的模型名称。
        例如：传入 CHAT_CAPABILITY，可能返回 "gpt-3.5-turbo"；
             传入 TRAINING_CAPABILITY，可能返回 "gpt-4o"。
        """
        raise NotImplementedError

    @abstractmethod
    def generate_text(self, *, system_prompt: str, user_prompt: str, capability: str) -> str:
        """
        生成单次完整的文本回复。
        
        核心细节：参数列表里的 `*` 是 Python 的一个特殊语法，叫“强制关键字参数 (Keyword-Only Arguments)”。
        它要求调用者在调用这个方法时，必须显式地写出参数名。
        例如：
        ❌ 错误调用：client.generate_text("你是AI", "帮我写代码", "chat")
        ✅ 正确调用：client.generate_text(system_prompt="你是AI", user_prompt="帮我写代码", capability="chat")
        这样可以极大地提高代码的可读性，防止参数传错位置。
        """
        raise NotImplementedError

    @abstractmethod
    def stream_text(self, *, system_prompt: str, user_prompt: str, capability: str) -> Iterator[str]:
        """
        以流式 (Streaming) 方式生成文本回复，类似于 ChatGPT 打字机的效果。
        返回的是一个 Python 迭代器 (Iterator[str])，调用方可以通过 for 循环逐步获取生成的文本块 (chunk)。
        """
        raise NotImplementedError

    @abstractmethod
    def generate_json(self, *, system_prompt: str, user_prompt: str, capability: str) -> dict[str, Any]:
        """
        强制模型生成 JSON 格式的数据，并解析为 Python 字典。
        非常适合用于我们在前几个文件中定义的，需要精确字段映射的场景（比如生成复杂的训练计划响应体）。
        """
        raise NotImplementedError