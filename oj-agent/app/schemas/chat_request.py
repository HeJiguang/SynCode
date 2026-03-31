# 从 typing 模块导入 Any 类型，用于表示"任意类型"，在 model_validator 的参数中使用
from typing import Any

# 从 pydantic 库导入以下内容：
# - BaseModel: 所有数据模型的基类，提供自动校验、序列化等能力
# - ConfigDict: 用于配置模型行为的字典类型
# - Field: 用于为模型字段添加元信息（描述、默认值、校验规则等）
# - model_validator: 装饰器，用于在字段校验前/后执行自定义校验逻辑
from pydantic import BaseModel, ConfigDict, Field, model_validator


# 定义"对话请求"数据模型
# 继承 BaseModel 后，Pydantic 会自动对传入的数据进行类型校验
# 当前端或其他服务发送一个 HTTP 请求到聊天接口时，请求体会被映射到这个类的实例上
class ChatRequest(BaseModel):
    # 请求链路追踪 ID（可选）
    # 用于在分布式系统中追踪同一次请求经过的所有服务节点，方便排查问题
    # `str | None` 表示类型为字符串或 None（Python 3.10+ 的联合类型写法）
    # `default=None` 表示不传时默认为 None，即该字段为可选字段
    trace_id: str | None = Field(default=None, description="Request trace identifier")

    # 当前发起请求的用户 ID（可选）
    # 用于识别是哪个用户在提问，方便后续关联用户历史记录或做个性化回答
    user_id: str | None = Field(default=None, description="Current user identifier")

    # 当前对话的会话 ID（可选）
    # 同一个对话中的多次提问会共享同一个 conversation_id，用于维护多轮上下文
    conversation_id: str | None = Field(default=None, description="Conversation id")

    # 用户当前正在做的题目 ID（可选）
    # AI 可以根据这个 ID 去查询题目的详细信息，为回答提供更准确的上下文
    question_id: str | None = Field(default=None, description="Current OJ question id")

    # 用户当前正在做的题目标题（可选）
    # 在 AI 的回答中直接引用题目名称，使回答更具针对性
    question_title: str | None = Field(default=None, description="Current OJ question title")

    # 题目的完整题面内容（可选）
    # 将原题内容传给 AI，使 AI 能理解题目要求，从而给出更精准的提示或解析
    question_content: str | None = Field(default=None, description="Current OJ problem statement")

    # 用户当前编写的代码（可选）
    # AI 会结合这段代码来分析用户遇到的问题，比如指出代码中的 bug
    user_code: str | None = Field(default=None, description="User code under discussion")

    # 最近一次判题（代码提交）的结果摘要（可选）
    # 例如："编译错误：第5行缺少分号" 或 "运行超时"
    # AI 可以根据这个信息直接给出针对该错误的解决方案
    judge_result: str | None = Field(default=None, description="Latest judge result summary")

    # 用户本次发送的消息内容（必填）
    # `...`（省略号）在 Pydantic 中表示该字段为必填项，不传该字段则请求直接报错
    user_message: str = Field(..., description="Latest user message")

    # 模型级别的配置项
    # `populate_by_name=True` 表示允许同时通过字段名（snake_case）和别名（alias）来赋值
    # 与下面的 normalize_camel_case 方法配合使用
    model_config = ConfigDict(populate_by_name=True)

    # 使用 @model_validator 装饰器定义一个"预校验"钩子函数
    # `mode="before"` 表示在 Pydantic 对各个字段做类型校验【之前】执行这个钩子
    # `@classmethod` 表示这是类方法，第一个参数 `cls` 代表类本身而不是实例
    @model_validator(mode="before")
    @classmethod
    # 函数名 normalize_camel_case 表示"规范化驼峰命名"
    # 参数 `data: Any` 是原始传入的数据（通常是一个字典），返回值也是处理后的数据
    # 返回值类型标注 `-> Any` 表示返回任意类型
    def normalize_camel_case(cls, data: Any) -> Any:
        # 如果传入的数据不是字典类型（例如是已实例化的对象），则直接原样返回，不做任何处理
        if not isinstance(data, dict):
            return data

        # 复制一份传入数据的字典，避免直接修改原始数据（防止副作用）
        normalized = dict(data)

        # 定义驼峰命名（前端/Java 风格）到蛇形命名（Python 风格）的映射关系
        # key: 前端传来的驼峰格式字段名
        # value: Python 模型中对应的蛇形格式字段名
        key_map = {
            "traceId": "trace_id",           # 链路追踪 ID
            "userId": "user_id",             # 用户 ID
            "conversationId": "conversation_id",  # 会话 ID
            "questionId": "question_id",     # 题目 ID
            "questionTitle": "question_title",    # 题目标题
            "questionContent": "question_content",  # 题目内容
            "userCode": "user_code",         # 用户代码
            "judgeResult": "judge_result",   # 判题结果
            "userMessage": "user_message",   # 用户消息
        }

        # 遍历映射表，将传入数据中的驼峰命名键替换为蛇形命名键
        for source_key, target_key in key_map.items():
            # 条件：传入数据中存在该驼峰键，且尚未存在对应的蛇形键（防止覆盖已有正确格式的数据）
            if source_key in normalized and target_key not in normalized:
                # 将驼峰键的值复制到蛇形键上（注意：驼峰键的值保留不删除，两者并存）
                normalized[target_key] = normalized[source_key]

        # 返回处理后的字典，Pydantic 接着用这个字典来填充模型字段
        return normalized
