from typing import Any
from pydantic import BaseModel, Field
from app.runtime.enums import RiskLevel, RunStatus, TaskType

# ============================================================================
# 1. 请求上下文 (RequestContext)
# 作用：这是“输入端”，包含了用户发起请求时带来的所有原始材料。节点一般只读不改。
# ============================================================================
class RequestContext(BaseModel):
    trace_id: str             # 链路追踪ID，用于在日志系统里串联起这一次请求的所有日志，方便排查报错。
    user_id: str              # 当前发消息的用户ID（学号等）。
    task_type: TaskType       # 任务类型，告诉系统这是普通聊天(CHAT)、错题诊断(DIAGNOSIS) 还是学习计划(TRAINING_PLAN)。
    user_message: str         # 用户实际发出的文本消息，比如："我这题为什么超时了？"
    conversation_id: str | None = None # 会话ID，用于让大模型去数据库里捞之前的历史聊天记录。
    
    # --- 下面是 Bite-OJ 业务强相关的上下文 ---
    question_id: str | None = None      # 题目ID（如果用户是在某道题目的页面提问的）。
    question_title: str | None = None   # 题目名称，比如 "两数之和"。
    question_content: str | None = None # 题目描述正文。
    user_code: str | None = None        # 用户当前页面里写出的代码。
    judge_result: str | None = None     # 判卷机返回的结果，比如 "Wrong Answer", "Time Limit Exceeded"。
    exam_id: str | None = None          # 考试ID（如果在考试中）。
    plan_id: str | None = None          # 学习计划ID。

# ============================================================================
# 2. 执行状态 (ExecutionState)
# 作用：这是“系统内部使用的监控器”，记录当前这套流程跑到哪一步了，用于重试或排错。
# ============================================================================
class ExecutionState(BaseModel):
    run_id: str                    # LangGraph 或引擎为这一次运行生成的唯一流水号。
    graph_name: str                # 跑的是哪个图，比如 "supervisor_graph" 或 "tutor_graph"。
    status: RunStatus              # 当前状态（运行中、成功、失败）。
    active_node: str | None = None # 当前正在执行的具体节点名字，比如正在执行 "retrieval_node"。
    retry_count: int = 0           # 重试次数。大模型由于网络或幻觉经常失败，如果失败了可以根据这个数来判断是否重试。
    branch_name: str | None = None # 记录走了图的哪条分支。
    fallback_type: str | None = None # 如果主流程彻底失败了，降级处理的类型（告诉前端“当前大模型繁忙”等）。
    model_name: str | None = None  # 记录最终是谁回答的这个问题（比如 gpt-4o, claude-3-5-sonnet）。

# ============================================================================
# 3. 证据/检索状态 (EvidenceState)
# 作用：这是 RAG（检索增强生成）专用的模块。大模型记忆有限，回答前系统会去数据库里捞资料（证据）放进这里。
# ============================================================================
class EvidenceItem(BaseModel):
    # 这一块代表了【单条】被检索回来的资料
    evidence_id: str               # 资料ID。
    source_type: str               # 来源类型（来自知识库文档、类似题目、还是学生的历史错题）。
    source_id: str                 # 外部引用来源的ID。
    title: str | None = None       # 资料标题。
    snippet: str                   # 资料的具体片段/正文。比如一段官方满分代码。
    recall_score: float | None = None  # 初排得分（向量检索匹配度有多高）。
    rerank_score: float | None = None  # 重排得分（经过更复杂的模型确认相关度的得分）。
    trust_label: str | None = None     # 信任度标签（比如这资料是人工审核过的，还是网上抓的）。
    metadata: dict[str, Any] = Field(default_factory=dict) # 存一些杂项属性。

class EvidenceState(BaseModel):
    # 这一块是所有被检索资料的【大集合】
    items: list[EvidenceItem] = Field(default_factory=list) # 存放上面 EvidenceItem 的列表。这通常会被组装进 Prompt 里。
    route_names: list[str] = Field(default_factory=list)    # 系统去哪里查的，比如 ["dense_vector", "sql_database"]。
    coverage_score: float | None = None                     # 查出来的资料有多能解决用户的问题（覆盖率）。

# ============================================================================
# 4. 护栏/安全状态 (GuardrailState)
# 作用：AI 领域的“保安”。在调用大模型前查一查用户有没有乱问，模型回答后查一查模型有没有乱说。
# ============================================================================
class GuardrailState(BaseModel):
    risk_level: RiskLevel = RiskLevel.LOW # 风险等级：高(HIGH)中(MEDIUM)低(LOW)。比如用户问“直接给我正确代码不要讲解”，算高风险。
    completeness_ok: bool = False         # 信息是否完整？比如你想诊断错误，但上下文根本没传 user_code，这里就会是 False。
    policy_ok: bool = True                # 是否符合业务政策/安全合规。（是否涉黄涉政、是否套系统Prompt）。
    dirty_data_flags: list[str] = Field(default_factory=list) # 记录少传了什么数据。
    risk_reasons: list[str] = Field(default_factory=list)     # 解释为什么会判定为高风险（用于日志和后续人工介入）。

# ============================================================================
# 5. 输出状态 (OutcomeState) 及其子件
# 作用：这是“输出端”，最终这个包裹处理完以后，要拿去给用户展示的话、或者要写进数据库的操作。
# ============================================================================
class WriteIntent(BaseModel):
    # Python 端 Agent 不直接操作数据库（避免脏数据），它只会生成一个“写意图”交给 Java 后端去落库。
    intent_type: str        # 意图类型，比如 "update_user_profile" (更新用户能力画像)。
    target_service: str     # 需要指派给哪个 Java 微服务，比如 "oj-friend"。
    payload: dict[str, Any] = Field(default_factory=dict) # 要存入的具体数据JSON。

class OutcomeState(BaseModel):
    intent: str | None = None             # 大模型推断出用户真实在干嘛，比如 "ASK_FOR_HINT" (求提示) 或 "COMPLAIN" (抱怨难)。
    answer: str | None = None             # ！！！大模型生成的最终文本回复，也就是展示在前端对话框里的话。
    next_action: str | None = None        # 给前端 UI 的提示，比如下一步建议用户点什么按钮 ("Send one more concrete failing example.")
    confidence: float | None = None       # 模型对自己这波回答多自信 (0.0 到 1.0)。
    status_events: list[dict[str, str]] = Field(default_factory=list) # 运行步骤日志，比如 "正在查阅相似题目..." (前端可以用来做炫酷的 Loading 动画)。
    response_payload: dict[str, Any] = Field(default_factory=dict)    # 给前端或者 Java 提供的一些额外结构化数据。
    write_intents: list[WriteIntent] = Field(default_factory=list)    # 挂载上面定义的 WriteIntent。

# ============================================================================
# 6. 统一 Agent 状态 (UnifiedAgentState)
# 作用：最核心的数据载体。所有的节点(Nodes)都是在操作这一个对象。
# 比如 `RetrievalNode` 负责往 `evidence` 里填东西；
#    `GuardrailNode` 负责往 `guardrail` 里填东西；
#    `LLMGenerateNode` 阅读 request 和 evidence，最后把回答写进 `outcome.answer` 里。
# ============================================================================
class UnifiedAgentState(BaseModel):
    request: RequestContext   # (输入) 我收到了什么
    execution: ExecutionState # (控制) 我跑到哪了
    evidence: EvidenceState   # (扩展) 我查到了什么外部资料
    guardrail: GuardrailState # (风控) 这波安不安全
    outcome: OutcomeState     # (输出) 我最后要吐出什么
