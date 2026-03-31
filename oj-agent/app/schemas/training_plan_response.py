from datetime import datetime

from pydantic import BaseModel, Field


class TrainingPlanTask(BaseModel):
    """
    训练计划任务模型 (TrainingPlanTask)
    代表生成的训练计划中的某一个具体任务（可能是一道题，也可能是一场测试）。
    """
    # 任务类型，必填项。通常业务上会定义为枚举类型，比如 "question" 或 "test"
    task_type: str = Field(..., description="Task type such as question or test")
    
    # 如果 task_type 是 "question"，则此字段记录对应的题目ID；否则为 None
    question_id: int | None = Field(default=None, description="Question id when task type is question")
    # 如果 task_type 是 "test"，则此字段记录对应的测试/考试ID；否则为 None
    exam_id: int | None = Field(default=None, description="Test id when task type is test")
    
    # 任务标题的快照，必填项。
    # 核心细节：命名带有 'snapshot' 是很好的工程实践。这意味着它记录的是“生成计划那一刻”的标题，
    # 即使未来题库里的题目改名了，这份历史计划里的标题依然保持不变，避免数据状态混乱。
    title_snapshot: str = Field(..., description="Task title")
    
    # 任务在整个训练计划中的顺序/序号，必填项，用于前端按顺序渲染
    task_order: int = Field(..., description="Ordered position in the plan")
    
    # AI 或系统推荐该任务的理由（例如：“这道题针对你近期薄弱的动态规划进行了强化”），选填
    recommended_reason: str | None = Field(default=None, description="Why this task was recommended")
    
    # 知识点标签的快照，选填，记录生成任务时的知识点状态
    knowledge_tags_snapshot: str | None = Field(default=None, description="Knowledge tags snapshot")
    
    # 建议完成该任务的截止时间，选填
    due_time: datetime | None = Field(default=None, description="Recommended completion time for the task")


class TrainingPlanResponse(BaseModel):
    """
    训练计划响应模型 (TrainingPlanResponse)
    作为最终结果返回给前端或调用方的完整数据结构，包含了全局分析和具体的任务列表。
    """
    # 最终确认/解析出的用户当前技术水平，必填项
    current_level: str = Field(..., description="Resolved current level")
    # 最终确认/解析出的用户学习目标方向，必填项
    target_direction: str = Field(..., description="Resolved target direction")
    
    # 基于用户历史数据（recent_submissions）分析出的薄弱点总结，必填项
    weak_points: str = Field(..., description="Weak points summary")
    # 分析出的优势点总结，必填项
    strong_points: str = Field(..., description="Strong points summary")
    
    # 为这份训练计划生成的标题（例如：“冲刺大厂：中级算法突破计划”），必填项
    plan_title: str = Field(..., description="Plan title")
    # 这份训练计划的核心目标，必填项
    plan_goal: str = Field(..., description="Plan goal")
    # AI 对用户的整体学习建议或本次计划的导语总结，必填项
    ai_summary: str = Field(..., description="Plan summary")
    
    # 核心细节：该计划包含的具体任务列表。
    # 再次使用了 default_factory=list，确保如果业务逻辑没有生成任何任务，返回的也是一个安全的空列表 [] 而不是 None 或共享引用。
    tasks: list[TrainingPlanTask] = Field(default_factory=list, description="Generated tasks")