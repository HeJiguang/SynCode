# Question Curation Tool

Local web tool for curating candidate programming problems before importing them into OnlineOJ.

## Run

```bash
uvicorn app.main:create_app --factory --reload --app-dir tool/question-curation
```

## Environment

Copy `.env.example` and configure:

```bash
QUESTION_CURATION_OJ_DATABASE_URL=mysql+pymysql://user:password@host:3306/dbname?charset=utf8mb4
QUESTION_CURATION_IMPORT_CREATE_BY=1
QUESTION_CURATION_LLM_ENABLED=true
QUESTION_CURATION_LLM_BASE_URL=https://api.openai.com/v1
QUESTION_CURATION_LLM_API_KEY=your_key
QUESTION_CURATION_LLM_MODEL=gpt-4.1-mini
```

The tool keeps its own local SQLite workspace and only writes to the OnlineOJ database when:

- the candidate has been manually approved
- `QUESTION_CURATION_OJ_DATABASE_URL` is configured

AI generation:

- if the `QUESTION_CURATION_LLM_*` variables are configured, the tool will try AI-first candidate generation
- if AI is not configured or the request fails, the tool falls back to the built-in rule generator

## First-Use Flow

1. Open `/candidates`
2. Create a candidate
3. Fill in statement, tags, limits, `question_case_json`, Java code fields
4. Click `Approve Candidate`
5. Click `Import Into OnlineOJ`

## Test

```bash
pytest tool/question-curation/tests -v
```
