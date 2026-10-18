---
name: syncode-training-plan
description: 根据个人学习数据制定可执行的算法训练安排。
version: 1.4.0
metadata:
  hermes:
    tags: [education, planning, practice]
    category: education
---

# SynCode 训练规划

## 何时使用

当学生询问接下来练什么、如何补弱项、如何安排复习，或希望调整训练节奏时使用。

## 工作流

1. 调用 `get_my_learning_profile` 了解已保存的水平、目标、强项、弱项和做题统计。
2. 阅读 Hermes 核心上下文自动召回的薄弱知识点、证据置信度、趋势和到期复习项。
3. 对优先知识点使用自动召回的 `pattern` 和 `episode` 理解具体错误原因；需要核实来源时调用详情工具。
4. 调用 `get_my_current_training_plan`，避免重复安排正在进行的任务。
5. 根据目标和带证据的学习状态选择一到两个当前重点，不要一次覆盖所有知识点。
6. 用 `search_practice_questions` 查找未通过、难度合适且标签相关的题目。
7. 给出一个短周期安排，默认 3 到 7 个任务；每项说明目的、顺序和完成标准。

## 应用生成模式

当系统要求输出 `TrainingPlanResponse`，或上下文中提供了 `candidate_questions` / `candidate_exams` 时，进入应用生成模式：

1. 把用户本轮自然语言诉求作为首要约束，同时结合 Profile 中的长期目标、偏好和学习记忆。
2. 仍按上述工作流调用只读工具；候选题上下文是最终允许落库的白名单，MCP 检索用于核实适配度和排除当前计划重复项。
3. 只选择候选上下文中真实存在的 `question_id` 或 `exam_id`。无法找到合法任务时返回空 `tasks`，不得编造 ID。
4. 只输出一个 JSON 对象，不使用 Markdown 代码块，也不附加解释。结构必须是：

```json
{
  "current_level": "string",
  "target_direction": "string",
  "weak_points": "string",
  "strong_points": "string",
  "plan_title": "string",
  "plan_goal": "string",
  "ai_summary": "string",
  "tasks": [
    {
      "task_type": "review | question | test",
      "question_id": 0,
      "exam_id": null,
      "title_snapshot": "string",
      "task_order": 1,
      "recommended_reason": "string",
      "knowledge_tags_snapshot": "string",
      "due_time": null
    }
  ]
}
```

`question` 和 `review` 任务必须设置合法 `question_id` 且令 `exam_id` 为 `null`；`test` 任务必须设置合法 `exam_id` 且令 `question_id` 为 `null`。`task_order` 从 1 连续递增，任务数量尽量遵循 `preferred_count`。

## 规划原则

- 数据不足时先给保守方案，并指出还需要观察什么。
- 优先处理掌握度低、置信度足够或已到复习时间的知识点；低置信度结论只安排探索性任务。
- 难度逐步上升，穿插一道复习题，避免连续堆叠陌生技巧。
- 训练任务必须具体到题目或明确练习动作。
- 工具始终只读。对话模式下不声称已经写入计划；应用生成模式下，用户点击“生成计划”即授权 SynCode 校验并保存提案，但 Skill 本身仍不得执行写入。
- 不因一次失败永久判断学生能力；长期判断应参考多次提交与训练记录。
- Hermes 原生记忆中的目标和教学偏好可以参与规划；动态能力结论必须以学习记忆工具的最新结果为准。

## 输出要求

对话模式下，先用一两句话说明本轮重点，再列出按顺序执行的任务。每个任务包含题目、训练目的和通过标准，最后说明什么时候应该回来复盘或调整计划。应用生成模式严格遵循上面的 JSON 要求。

## 完成检查

确认推荐题来自真实工具结果，没有重复当前计划，任务数量可在一周内完成，并且每项都有可判断的完成标准。
