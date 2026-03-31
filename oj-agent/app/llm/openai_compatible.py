from collections.abc import Iterator
import json
from typing import Any

from app.core.config import AgentSettings
from app.llm.base import CHAT_CAPABILITY, LLMClient, TRAINING_CAPABILITY


class OpenAICompatibleLLMClient(LLMClient):
    """
    OpenAI 兼容的大语言模型客户端。
    
    无论是官方的 OpenAI，还是通过 vLLM、Ollama 本地部署的开源模型（如 Qwen, Llama），
    只要它们提供了兼容 OpenAI 格式的 API，都可以使用这个客户端。
    """
    def __init__(self, settings: AgentSettings) -> None:
        # 将系统配置保存下来，包含了 API Key、Base URL、温度参数(Temperature)等
        self.settings = settings
        # 内部的 openai 客户端实例，初始化为 None，使用“懒加载”模式
        self._client = None

    def is_available(self) -> bool:
        """
        检查配置是否足够发起调用：必须有 API Key，并且至少配置了一个模型（聊天或训练）。
        """
        return bool(self.settings.llm_api_key and (self.settings.chat_model or self.settings.training_model))

    def model_name(self, capability: str) -> str:
        """
        模型路由逻辑：根据传入的能力需求，返回对应的模型名称。
        在实际业务中，简单的聊天可能用便宜快的小模型，而复杂的训练计划生成则用推理能力强的大模型。
        """
        if capability == TRAINING_CAPABILITY and self.settings.training_model:
            return self.settings.training_model
        if capability == CHAT_CAPABILITY and self.settings.chat_model:
            return self.settings.chat_model
        # 降级策略：如果没配置对应的专属模型，就用另一个顶上，或者返回 "unknown-model"
        return self.settings.chat_model or self.settings.training_model or "unknown-model"

    def generate_text(self, *, system_prompt: str, user_prompt: str, capability: str) -> str:
        """
        向大模型发起同步的文本生成请求。
        """
        # 调用 _client_instance() 确保内部的 openai 客户端已经初始化
        message = self._client_instance().chat.completions.create(
            model=self.model_name(capability),
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = message.choices[0].message.content
        # 防御性返回：确保返回的一定是字符串，即便大模型 API 抽风返回了 None
        return content if isinstance(content, str) else str(content or "")

    def stream_text(self, *, system_prompt: str, user_prompt: str, capability: str) -> Iterator[str]:
        """
        向大模型发起流式 (Streaming) 请求，实现打字机效果。
        """
        stream = self._client_instance().chat.completions.create(
            model=self.model_name(capability),
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,  # 开启流式输出
        )
        # 遍历返回的流式数据块 (chunk)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            # 通过 yield 关键字，将每次收到的小段文本实时“吐”给上层业务代码
            if isinstance(delta, str) and delta:
                yield delta

    def generate_json(self, *, system_prompt: str, user_prompt: str, capability: str) -> dict[str, Any]:
        """
        请求大模型并强制解析为 JSON。
        """
        # 复用 generate_text 方法获取原始字符串
        text = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            capability=capability,
        )
        # 使用专门的清洗函数提取和解析 JSON
        return _extract_json_object(text)

    def _client_instance(self):
        """
        懒加载 (Lazy Loading) 实例化底层的 openai 客户端。
        核心细节：为什么不在文件开头 import openai，而是在这里？
        因为如果用户在配置中完全禁用了 LLM 功能，系统甚至不需要安装 openai 这个包。
        把 import 放在这里，可以加快系统启动速度，并减少不必要的依赖报错。
        """
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("openai package is not installed") from exc

            self._client = OpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
                timeout=self.settings.llm_timeout_seconds,
            )
        return self._client


def _extract_json_object(text: str) -> dict[str, Any]:
    """
    JSON 脏数据清洗工具函数。
    
    工程痛点：大模型（即便是很聪明的模型）在被要求输出 JSON 时，
    经常会“自作多情”地在前后加上 Markdown 标记，比如：
    ```json
    { "key": "value" }
    ```
    或者在 JSON 后面附带一句 "这就是为您生成的 JSON。"
    
    这个函数通过寻找第一个 '{' 和最后一个 '}'，暴力裁剪掉所有多余的字符，
    从而极大提高了 JSON 解析的成功率。
    """
    stripped = text.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    
    # 如果找不到花括号，或者右括号在左括号前面，说明大模型彻底胡言乱语了
    if start < 0 or end < 0 or end <= start:
        raise ValueError("model response did not contain a JSON object")
        
    # 截取 '{' 和 '}' 之间的纯净字符串并解析为 Python 字典
    return json.loads(stripped[start : end + 1])