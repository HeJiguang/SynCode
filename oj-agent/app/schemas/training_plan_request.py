from datetime import datetime

from pydantic import BaseModel, Field


class SubmissionSnapshot(BaseModel):
    """
    提交快照模型 (SubmissionSnapshot)
    用于记录用户最近一次代码提交的简要信息。
    """
    # 提交记录的唯一ID。'| None' 表示该字段可以为 None，default=None 设定了默认值。
    submit_id: int | None = Field(default=None, description="Submit id")
    # 对应的题目ID
    question_id: int | None = Field(default=None, description="Question id")
    # 对应的考试/测试ID
    exam_id: int | None = Field(default=None, description="Test id")
    # 题目名称
    title: str | None = Field(default=None, description="Question title")
    # 题目难度级别
    difficulty: int | None = Field(default=None, description="Question difficulty")
    # 主要的算法标签（例如：动态规划、贪心等）
    algorithm_tag: str | None = Field(default=None, description="Primary algorithm tag")
    # 相关的知识点标签，多个标签通常用逗号分隔
    knowledge_tags: str | None = Field(default=None, description="Comma separated knowledge tags")
    
    # 判题是否通过的标志。
    # 核心细节：由于 'pass' 是 Python 的保留关键字，不能直接用作变量名。
    # 所以这里变量名命名为 'pass_'，并通过 alias="pass" 告诉 Pydantic 在解析/输出 JSON 时使用 'pass' 这个键。
    pass_: int | None = Field(default=None, alias="pass", description="Judge pass flag")
    
    # 提交的最终得分
    score: int | None = Field(default=None, description="Submit score")
    # 判题系统返回的执行信息（如编译错误信息、运行时报错等）
    exe_message: str | None = Field(default=None, description="Judge execution message")

    # Pydantic 模型配置：允许在实例化时，通过字段原名 (pass_) 或别名 (pass) 来填充数据
    model_config = {"populate_by_name": True}


class QuestionCandidate(BaseModel):
    """
    候选题目模型 (QuestionCandidate)
    用于表示可以被系统算法或 AI 选入最终训练计划的备选题目。
    """
    # 题目ID。使用 '...' (Ellipsis) 表示该字段是必填项，没有默认值。
    question_id: int = Field(..., description="Question id")
    # 题目名称，必填项
    title: str = Field(..., description="Question title")
    # 题目难度，选填
    difficulty: int | None = Field(default=None, description="Question difficulty")
    # 主要的算法标签，选填
    algorithm_tag: str | None = Field(default=None, description="Primary algorithm tag")
    # 相关的知识点标签，选填
    knowledge_tags: str | None = Field(default=None, description="Comma separated knowledge tags")
    # 预估完成该题目所需的分钟数，选填
    estimated_minutes: int | None = Field(default=None, description="Estimated solving time")


class ExamCandidate(BaseModel):
    """
    候选阶段测试模型 (ExamCandidate)
    用于表示可以被选入训练计划的备选阶段测试/考试。
    """
    # 测试ID，必填
    exam_id: int = Field(..., description="Stage test id")
    # 测试标题，必填
    title: str = Field(..., description="Stage test title")
    # 测试开始时间，选填（使用 Pydantic 自动转换和验证的 datetime 类型）
    start_time: datetime | None = Field(default=None, description="Stage test start time")
    # 测试结束时间，选填
    end_time: datetime | None = Field(default=None, description="Stage test end time")


class TrainingPlanRequest(BaseModel):
    """
    训练计划请求模型 (TrainingPlanRequest)
    用于接收前端或其他微服务发来的请求体，将用户的历史数据和所有的候选库打包在一起，
    以便后端生成定制化的训练计划。
    """
    # 链路追踪ID，必填，主要用于微服务架构中的日志排查和请求全链路追踪
    trace_id: str = Field(..., description="Trace id")
    # 用户ID，必填
    user_id: int = Field(..., description="User id")
    # 用户当前的技术评级或等级，选填
    current_level: str | None = Field(default=None, description="Current level")
    # 用户设定的目标学习方向（比如：后端架构、算法竞赛等），选填
    target_direction: str | None = Field(default=None, description="Target direction")
    # 基于哪个特定的测试ID来生成计划（例如：根据某次期中考试的错题来生成弱点针对训练），选填
    based_on_exam_id: int | None = Field(default=None, description="Optional source test id")
    # 用户期望生成的任务（题目或测试）数量，选填
    preferred_count: int | None = Field(default=None, description="Preferred task count")
    
    # 核心细节：使用 default_factory=list 确保默认值是一个每次都新生成的空列表 []。
    # 如果直接写 default=[]，会导致所有未传该参数的请求实例共享同一个列表对象，从而引发难以排查的内存级 Bug。
    
    # 用户最近的提交记录快照列表
    recent_submissions: list[SubmissionSnapshot] = Field(default_factory=list, description="Recent submission summaries")
    # 系统提供给计划生成算法的候选题目集合
    candidate_questions: list[QuestionCandidate] = Field(default_factory=list, description="Candidate questions")
    # 系统提供给计划生成算法的候选测试集合
    candidate_exams: list[ExamCandidate] = Field(default_factory=list, description="Candidate stage tests")