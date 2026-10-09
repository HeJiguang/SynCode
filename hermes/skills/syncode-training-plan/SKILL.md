---
name: syncode-training-plan
description: 根据个人学习数据制定可执行的算法训练安排。
version: 1.0.0
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
2. 调用 `get_my_current_training_plan`，避免重复安排正在进行的任务。
3. 根据目标选择一到两个当前重点，不要一次覆盖所有知识点。
4. 用 `search_practice_questions` 查找未通过、难度合适且标签相关的题目。
5. 给出一个短周期安排，默认 3 到 7 个任务；每项说明目的、顺序和完成标准。
6. 先把计划展示给学生。只有学生明确表示接受或要求保存时，才调用 `save_my_training_plan`。
7. 复盘已有计划时调用 `get_my_training_effects`，根据完成、尝试和通过情况调整下一轮推荐。

## 规划原则

- 数据不足时先给保守方案，并指出还需要观察什么。
- 难度逐步上升，穿插一道复习题，避免连续堆叠陌生技巧。
- 训练任务必须具体到题目或明确练习动作。
- `save_my_training_plan`、`update_my_training_task` 和 `record_my_recommendation_feedback` 是受控写工具，必须经过 Hermes 的原生用户审批；不得绕过审批或代替用户作决定。
- 写入工具中的用户身份由服务端注入，不要请求或传入 `userId`。
- 不因一次失败永久判断学生能力；长期判断应参考多次提交与训练记录。

## 输出要求

先用一两句话说明本轮重点，再列出按顺序执行的任务。每个任务包含题目、训练目的和通过标准。最后说明什么时候应该回来复盘或调整计划。

## 完成检查

确认推荐题来自真实工具结果，没有重复当前计划，任务数量可在一周内完成，并且每项都有可判断的完成标准。
