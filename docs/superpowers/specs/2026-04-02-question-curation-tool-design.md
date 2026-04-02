# Question Curation Tool Design

Date: 2026-04-02
Status: Draft for user review
Scope: `D:\Project\OnlineOJ\bite-oj-master\bite-oj-master`
Target: standalone local web tool under `tool/question-curation/`

## 1. Summary

This design defines a standalone pure-Python local web tool for curating programming problems for the OnlineOJ project.

The tool is not part of the existing Java services or the existing Python runtime mainline.

It lives under:

- `tool/question-curation/`

It runs locally as an operator-facing review console and supports:

- collecting problem leads and reference material
- normalizing candidate problems into an OJ-ready schema
- generating solution and judge artifacts
- checking for duplicate or near-duplicate problems
- running example code locally before approval
- producing review packs
- importing only human-approved problems into the OnlineOJ database

All imports are gated by manual review.

The tool may use platforms such as LeetCode or Luogu as inspiration or reference input, but the system must treat those platforms as reference sources rather than as blindly trusted bulk-ingestion backends.

## 2. Product Goal

The tool should let one operator do the following in a single local workflow:

1. start from a problem lead, link, title, or pasted statement
2. collect and organize the useful material for that problem
3. transform the material into the current OnlineOJ-compatible question shape
4. generate standard answer, Java starter code, `mainFuc`, examples, and hidden judge cases
5. compare it against the existing database to detect duplicates or close variants
6. run the generated Java example locally for sanity checking
7. review the full problem package
8. approve or reject it
9. import approved problems into `tb_question`

This is a curation workstation, not an autonomous ingestion bot.

## 3. Hard Constraints

The tool must satisfy all of these constraints:

- pure Python implementation
- isolated from current application code paths
- stored under a dedicated directory in `tool/`
- local web backend rather than CLI-only
- all problem imports require manual review
- local code execution is supported for verification, but must be sandboxed and operator-visible
- the tool must support the current OnlineOJ `tb_question` shape
- the tool should preserve evidence and intermediate outputs so the operator can understand how a candidate was produced
- the first version should optimize for correctness and operator throughput, not for full automation or large-scale crawling

## 4. Why Standalone Instead Of Integrating Into Existing Services

The current repository already has production-facing Java services and an in-progress Python AI runtime.

This tool should not be embedded into those systems yet because:

- its job is content production and review, not online user serving
- it requires local execution of candidate code and review-heavy pages
- it needs operator-centric storage and audit surfaces that do not belong in the live product path
- the user explicitly wants a standalone tool under `tool/`
- separating it now reduces risk of polluting the current runtime refactor work

The import boundary should be narrow:

- read existing OnlineOJ question data
- write approved records into OnlineOJ tables

Everything else stays inside the tool.

## 5. Chosen Technical Approach

### 5.1 Stack

The V1 stack is:

- FastAPI
- Jinja2 templates
- HTMX for partial page updates
- SQLite for local working-state persistence
- SQLAlchemy for ORM and migrations
- Pydantic for request and internal data validation
- a small task runner abstraction inside the app process
- optional background task threads for long-running generation and duplicate analysis

This avoids the complexity of a full frontend build while keeping the review UI interactive enough for dense problem-audit pages.

### 5.2 Why This Stack

This stack is preferred because:

- it stays pure Python
- it is easy to run locally
- server-rendered pages suit information-dense review workflows
- HTMX is sufficient for state transitions, reruns, comparison panes, and execution logs
- SQLite is enough for a local operator workflow in V1
- the project can later move storage or background execution to a more robust setup without rewriting the whole UI

## 6. Top-Level Directory Layout

The tool should be created at:

- `tool/question-curation/`

Recommended layout:

- `tool/question-curation/app/`
- `tool/question-curation/app/main.py`
- `tool/question-curation/app/config.py`
- `tool/question-curation/app/db.py`
- `tool/question-curation/app/models/`
- `tool/question-curation/app/schemas/`
- `tool/question-curation/app/services/`
- `tool/question-curation/app/services/intake/`
- `tool/question-curation/app/services/normalize/`
- `tool/question-curation/app/services/dedup/`
- `tool/question-curation/app/services/solution/`
- `tool/question-curation/app/services/execution/`
- `tool/question-curation/app/services/importer/`
- `tool/question-curation/app/routes/`
- `tool/question-curation/app/templates/`
- `tool/question-curation/app/static/`
- `tool/question-curation/app/tasks/`
- `tool/question-curation/app/utils/`
- `tool/question-curation/data/`
- `tool/question-curation/data/review_packs/`
- `tool/question-curation/data/raw_sources/`
- `tool/question-curation/data/execution/`
- `tool/question-curation/data/sqlite/`
- `tool/question-curation/tests/`
- `tool/question-curation/pyproject.toml`
- `tool/question-curation/README.md`

## 7. Core Domain Model

The tool should not write into `tb_question` as its working area.

It needs its own local persistence model first.

### 7.1 CandidateProblem

Represents one candidate problem under review.

Core fields:

- `candidate_id`
- `title`
- `slug`
- `source_type`
- `source_platform`
- `source_url`
- `source_problem_id`
- `status`
- `difficulty`
- `algorithm_tag`
- `knowledge_tags`
- `estimated_minutes`
- `time_limit_ms`
- `space_limit_kb`
- `statement_markdown`
- `question_case_json`
- `default_code_java`
- `main_fuc_java`
- `risk_level`
- `created_at`
- `updated_at`

### 7.2 SourceArtifact

Stores raw material gathered for a candidate.

Fields:

- `artifact_id`
- `candidate_id`
- `kind`
- `source_label`
- `url`
- `content_path`
- `content_text`
- `metadata_json`
- `created_at`

This lets the operator review what material was used without relying on volatile remote pages later.

### 7.3 CandidateSolution

Stores generated or edited solution artifacts.

Fields:

- `solution_id`
- `candidate_id`
- `language`
- `solution_code`
- `solution_outline`
- `complexity_note`
- `correctness_note`
- `created_at`
- `updated_at`

### 7.4 CandidateJudgeCase

Stores structured example and hidden cases separately inside the tool, even though V1 import may collapse them into `questionCase`.

Fields:

- `case_id`
- `candidate_id`
- `case_type`
- `case_order`
- `input_text`
- `output_text`
- `note`
- `enabled`

`case_type` values in V1:

- `sample`
- `hidden`

### 7.5 DedupMatch

Stores duplicate-analysis output.

Fields:

- `match_id`
- `candidate_id`
- `matched_question_id`
- `matched_title`
- `title_similarity`
- `semantic_similarity`
- `tag_similarity`
- `io_similarity`
- `overall_similarity`
- `decision`
- `reason`

### 7.6 ReviewDecision

Stores human review.

Fields:

- `review_id`
- `candidate_id`
- `review_status`
- `review_comment`
- `reviewer_name`
- `reviewed_at`

### 7.7 ImportRecord

Stores import audit.

Fields:

- `import_id`
- `candidate_id`
- `import_status`
- `target_question_id`
- `sql_snapshot`
- `imported_at`

## 8. Candidate Status Machine

The candidate workflow should use explicit statuses:

- `DISCOVERED`
- `MATERIAL_COLLECTED`
- `NORMALIZED`
- `DEDUP_CHECKED`
- `ARTIFACTS_GENERATED`
- `REVIEW_READY`
- `APPROVED`
- `REJECTED`
- `IMPORTED`

Rules:

- only `REVIEW_READY` candidates can be reviewed
- only `APPROVED` candidates can be imported
- rejected candidates stay searchable
- imports are append-only in audit terms

## 9. User-Facing Pages

The local web tool should provide these pages in V1.

### 9.1 Dashboard

Shows:

- candidate counts by status
- recently updated candidates
- duplicate-risk queue
- import-ready queue
- latest execution failures

### 9.2 New Candidate Page

Supports:

- paste statement text
- create from title and notes
- create from reference URL
- upload structured JSON seed

This page creates a candidate record and a processing task.

### 9.3 Candidate List Page

Supports filtering by:

- status
- source platform
- risk level
- duplicate decision
- updated time

### 9.4 Candidate Detail Review Page

This is the main page of the tool.

It should show:

- basic metadata
- source material panel
- normalized statement
- tags and limits
- sample cases
- hidden cases
- standard solution
- Java starter code
- `mainFuc`
- dedup report
- local execution results
- review action buttons

### 9.5 Duplicate Analysis Page

Shows:

- matched existing OJ problems
- side-by-side statement diff summary
- tag and structure overlap
- final recommendation

### 9.6 Execution Page

Lets the operator:

- run the generated Java solution against sample cases
- run custom sanity checks
- inspect stdout, stderr, exit code, and elapsed time

### 9.7 Import Queue Page

Shows:

- approved candidates waiting for import
- SQL preview
- existing-title collision warnings
- import result history

## 10. Service Modules

### 10.1 Intake Service

Responsibilities:

- accept raw leads
- fetch or store reference material
- convert raw input into internal source artifacts

V1 rule:

- treat outside platform content as reference evidence, not as authoritative final structured data

### 10.2 Normalization Service

Responsibilities:

- convert raw materials into the canonical candidate shape
- generate draft title, tags, limits, and statement sections
- normalize whitespace, markdown, and case structures

### 10.3 Dedup Service

Responsibilities:

- load existing OnlineOJ questions
- compute title similarity
- compute semantic similarity
- compare tags and example I/O structure
- generate a human-readable dedup report

V1 can use a layered heuristic plus embedding-based similarity if a local model or API is configured.

### 10.4 Solution Service

Responsibilities:

- produce standard solution draft
- produce Java reference implementation
- produce starter code
- produce `mainFuc`
- produce examples and hidden-case drafts
- produce explanation notes for review

### 10.5 Execution Service

Responsibilities:

- compile and run local Java code
- execute per-case verification
- capture stdout, stderr, exit code, and timing
- surface failures in the review UI

### 10.6 Importer Service

Responsibilities:

- validate candidate is approved
- map candidate fields to OnlineOJ schema
- generate SQL preview
- execute import into OnlineOJ database
- record import audit

## 11. Mapping To Current OnlineOJ Schema

The current target schema is centered on `tb_question`.

V1 import mapping:

- candidate `title` -> `tb_question.title`
- candidate `difficulty` -> `tb_question.difficulty`
- candidate `algorithm_tag` -> `tb_question.algorithm_tag`
- candidate `knowledge_tags` -> `tb_question.knowledge_tags`
- candidate `estimated_minutes` -> `tb_question.estimated_minutes`
- candidate `training_enabled` -> `tb_question.training_enabled`
- candidate `time_limit_ms` -> `tb_question.time_limit`
- candidate `space_limit_kb` -> `tb_question.space_limit`
- candidate `statement_markdown` -> `tb_question.content`
- approved visible cases -> `tb_question.question_case`
- Java starter code -> `tb_question.default_code`
- Java main function -> `tb_question.main_fuc`

Important V1 compromise:

- the tool should internally distinguish `sample` and `hidden` cases
- the current OnlineOJ schema still only has one `questionCase` field
- until the main project schema is upgraded, V1 importer should support a configurable export policy

Recommended V1 export policy:

- import only approved sample cases into `question_case`
- retain hidden cases in the tool review pack and local database

This is safer than exposing all hidden cases through the current field.

## 12. Duplicate Detection Policy

Duplicate detection must not be title-only.

The V1 score should combine:

- title similarity
- statement semantic similarity
- tag overlap
- example I/O structure overlap

Recommended review thresholds:

- `overall >= 0.92`: probable duplicate
- `0.75 <= overall < 0.92`: similar problem, manual attention required
- `overall < 0.75`: probably distinct

The tool must not auto-reject.

It only flags and explains.

## 13. Local Code Execution Safety

The tool must support local example-code verification, but this is the most security-sensitive feature in the design.

V1 guardrails:

- execute only local operator-approved runs
- isolate execution under a dedicated working directory under `tool/question-curation/data/execution/`
- enforce timeouts
- enforce memory and output size limits where practical
- only expose execution through explicit UI actions
- store execution logs with candidate linkage
- show operator exactly what code and inputs are being run

V1 does not promise production-grade sandboxing.

It is a local operator tool.

That means the UI must make the trust model explicit:

- only run code you are comfortable executing on this machine

## 14. Review Pack Output

Every review-ready candidate should produce a persisted review pack JSON under:

- `tool/question-curation/data/review_packs/<candidate_id>.json`

The review pack should include:

- source summary
- normalized problem
- generated statement
- dedup matches
- standard solution
- Java starter code
- `mainFuc`
- visible and hidden cases
- execution summary
- risk flags
- import mapping preview

The review pack is both a UI backing artifact and a durable evidence bundle.

## 15. Database Integration

The tool should connect to the OnlineOJ database through a dedicated importer configuration.

The tool should be able to run without DB connectivity for most of the workflow.

Recommended modes:

- `offline review mode`: local SQLite only, import disabled
- `connected review mode`: local SQLite plus read access to OnlineOJ DB for duplicate analysis
- `import mode`: local SQLite plus write access for approved candidates

This allows development and review work even when the OJ database is not available.

## 16. Configuration

The tool should use environment-based config plus a local `.env`.

V1 config categories:

- app host and port
- SQLite path
- review pack path
- raw artifact path
- execution work directory
- OnlineOJ MySQL connection
- optional model or embedding provider configuration
- execution timeout settings
- import policy settings

## 17. API and UI Boundary

Although this is a server-rendered local web tool, the app should still be internally structured as:

- routes
- service layer
- data layer

Routes should stay thin.

Business logic belongs in services so later automation or CLI entry points can reuse the same functionality.

## 18. V1 MVP Scope

V1 should include:

- create candidate from pasted text, title, or URL
- store source artifacts
- normalize candidate data
- edit candidate metadata in UI
- generate Java solution and starter artifacts
- generate sample and hidden cases
- perform duplicate analysis against current OJ questions
- run local Java verification against sample cases
- approve or reject candidates
- import approved candidates into `tb_question`
- write review pack JSON

V1 should explicitly exclude:

- multi-user collaboration
- role-based auth
- remote deployment
- batch crawling of whole external platforms
- full autonomous approval
- multi-language full parity
- advanced distributed task queues

## 19. Implementation Order

Recommended implementation order:

1. bootstrap app skeleton and config
2. add SQLite models and migrations
3. implement candidate CRUD and dashboard pages
4. implement review-pack persistence
5. implement dedup against existing OJ DB
6. implement Java execution service
7. implement solution and case generation workflow
8. implement approval and import flow
9. harden logs, tests, and README

This order makes the review shell usable early, before the more complex generation features are complete.

## 20. Risks

Key risks:

- duplicate detection quality may be weak without a good semantic comparison backend
- local code execution can be dangerous if operators overtrust generated code
- imported `questionCase` may remain limited by the current OnlineOJ schema
- inspiration-driven generation from external sites may drift too close to original wording if not reviewed carefully
- if the tool tries to automate too much in V1, review quality will drop

## 21. Success Criteria

The design is successful if a single operator can:

- create a candidate problem locally
- review the full candidate package in a browser
- see duplicate warnings against the current OJ database
- run Java verification locally
- approve a problem
- import it into OnlineOJ
- later inspect exactly what was reviewed and imported

## 22. Decision Summary

The V1 decision set is:

- standalone pure-Python tool
- stored under `tool/question-curation/`
- local web console using FastAPI plus Jinja plus HTMX
- SQLite as the working-state store
- manual review required for all imports
- internal separation between candidate workspace and formal OnlineOJ DB
- explicit support for Java verification
- review-pack-first workflow
- importer only after approval
