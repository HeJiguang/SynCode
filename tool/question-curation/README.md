# 题库补充工具

一个独立运行的本地 Web 后台，用于抓取题目来源、生成候选题、人工审核，并在通过后导入 OnlineOJ。

## 启动方式

```bash
uvicorn app.main:create_app --factory --reload --app-dir tool/question-curation
```

## 环境变量

复制 `.env.example` 后，至少按需配置下面这些变量：

```bash
QUESTION_CURATION_OJ_DATABASE_URL=mysql+pymysql://user:password@host:3306/dbname?charset=utf8mb4
QUESTION_CURATION_IMPORT_CREATE_BY=1
QUESTION_CURATION_LLM_ENABLED=true
QUESTION_CURATION_LLM_BASE_URL=https://api.openai.com/v1
QUESTION_CURATION_LLM_API_KEY=your_key
QUESTION_CURATION_LLM_MODEL=gpt-4.1-mini
```

说明：

- 工具自己的候选题工作区使用本地 SQLite。
- 只有在候选题被人工审核通过后，并且配置了 `QUESTION_CURATION_OJ_DATABASE_URL`，工具才会写入 OnlineOJ 数据库。
- 如果配置了 `QUESTION_CURATION_LLM_*`，会优先走 AI 生成。
- 如果 AI 没配置或调用失败，会自动回退到内置规则生成。

## 首次使用流程

1. 打开 `/discover`
2. 导入单题链接或批量题目链接
3. 系统自动生成候选题草稿
4. 到 `/candidates` 和详情页中人工审核
5. 点击“通过审核”
6. 点击“导入 OnlineOJ”

## 运行测试

```bash
pytest tool/question-curation/tests -v
```
