---
name: syncode-learning-profile
description: 根据新的提交与训练效果生成需要用户审核的长期学习画像候选。
version: 1.0.0
metadata:
  hermes:
    tags: [education, profile, memory]
    category: education
---

# SynCode 学习画像更新

## 何时使用

仅在 SynCode 的定时画像更新工作流触发时使用。这个工作流不直接修改业务数据库，也不自行创建训练计划。

## 工作流

1. 调用 `get_my_learning_profile`，读取累计提交数、已通过题数和已有训练画像。
2. 调用 `get_my_recent_submissions`，默认读取最近 20 次提交，观察多次出现的稳定表现。
3. 调用 `get_my_current_training_plan`。存在计划时，再调用 `get_my_training_effects` 检查完成、尝试和通过情况。
4. 将证据压缩为一条简短画像，内容可包含当前水平、稳定强项、需要加强的知识点、训练节奏和近期目标。
5. 调用 Hermes 原生 `memory` 工具，`target` 必须是 `user`。已有 `[SynCode 学习画像]` 条目时用 `replace`，否则用 `add`。
6. `memory.write_approval` 会把修改保存成候选。看到“staged for approval”就停止，不要重复调用，不要尝试绕过审核。

## 判断规则

- 只写由多次提交或训练效果支持的结论，不因一次错误给学生贴标签。
- 区分“尚未练习”和“反复出错”；证据不足时明确写“仍需观察”。
- 不保存源代码、报错全文、提交 ID、运行 ID、邮箱、用户 ID 或其他敏感信息。
- 画像控制在 600 个中文字符以内，使用完整、易读的一条 Markdown 文本。
- 不把临时任务、一次性计划进度或系统实现细节写入长期画像。
- 用户身份由受控工具自动绑定；不得询问、猜测或向工具传入 `userId`。

## 推荐格式

`[SynCode 学习画像] 水平：...；稳定强项：...；待加强：...；学习节奏：...；近期目标：...；证据状态：...。`

## 完成检查

确认读取的都是当前用户的数据，结论有多条证据支持，并且最终只产生一个等待用户审核的 `USER.md` 候选。
