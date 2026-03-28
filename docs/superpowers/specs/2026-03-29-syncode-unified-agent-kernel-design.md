# SynCode Unified Agent Kernel Design

Date: 2026-03-29
Status: Draft for user review
Scope: `D:\Project\OnlineOJ\bite-oj-master\bite-oj-master`

## 1. Summary

SynCode will evolve from the current `oj-agent` phase-1 assistant into a production-oriented unified agent kernel.

The new kernel will be built in Python with native LangChain and LangGraph patterns and will serve only SynCode.

It will unify these product scenes under one runtime:

- problem-solving tutoring
- failure diagnosis
- problem recommendation
- training-plan generation
- post-test and post-training review
- continuous profile update

The target is not a demo orchestrator.

The target is a deployable agent system with:

- graph-native reasoning and planning
- retrieval as a first-class runtime
- guardrails and hallucination interception
- full traceability and replay
- automated evaluation pipelines
- strong Java/Python service boundaries

## 2. Goals

- Replace the current heuristic-first toy pipeline with a real graph-centered agent runtime.
- Make LangGraph the control plane of the agent system instead of a shallow preprocessing layer.
- Build one unified runtime that supports multiple SynCode learning scenes without collapsing into one giant graph.
- Treat retrieval, tool execution, guardrails, evaluation, and observability as first-class subsystems.
- Keep all business writes inside Java domain services while letting the Python agent own planning and decision-making.
- Ship a version that can be deployed on SynCode production infrastructure instead of only local development.

## 3. Non-goals

- Build a general-purpose multi-tenant agent platform for arbitrary businesses.
- Make Neo4j or GraphRAG a hard dependency in phase 1 of this redesign.
- Move Java business-domain logic into Python.
- Let the agent directly mutate business data stores.
- Solve every future enterprise feature in the first delivery.

## 4. Product and Deployment Constraints

The design is constrained by the accepted operating model:

- The system serves SynCode only.
- The Python side owns the agent kernel.
- The Java side keeps domain services, validation, persistence, and the existing platform APIs.
- Judge remains on a separate small server because it couples to sandboxed execution.
- Agent-facing stateless services should run on Aliyun SAE.
- Managed cloud middleware should be preferred where possible to reduce operational cost.
- The first phase should be aggressive in capability, but still realistic to deploy and operate.

## 5. Current System Problems

The current repository shows several architectural limitations:

- `oj-agent` uses LangGraph only as a shallow deterministic state pipeline.
- final answer generation happens outside the graph through a separate `chat_assistant` step.
- training plan generation is also outside a reusable graph runtime.
- conversation state is still tied to in-process memory.
- retrieval is a lightweight keyword scan over markdown files rather than a real retrieval runtime.
- production concerns such as replay, evaluation, checkpointing, and full traceability are not first-class.

This redesign exists to remove those structural limits rather than layering more features on top of them.

## 6. Recommended Architecture

### 6.1 Chosen direction

Adopt a unified kernel plus subsystem architecture:

- one Python `agent-runtime`
- one `SupervisorGraph`
- multiple specialized capability subgraphs
- shared retrieval, tool, guardrail, evaluation, and observability runtimes

This is preferred over a single giant graph because SynCode already needs multiple capability families and production controls.

### 6.2 Top-level layers

- `agent-runtime`
  - unified Python service entrypoint
  - graph orchestration
  - checkpoint and execution control
  - model routing
  - token budgeting and runtime throttling
- `retrieval-runtime`
  - ingestion, indexing, multi-route recall, reranking, evidence assembly
- `tool-runtime`
  - standard tool contracts to Java domain services and platform capabilities
- `guardrail-runtime`
  - dirty-data handling, hallucination interception, evidence checks, policy gates
- `evaluation-runtime`
  - offline evaluation, CI regression, quality metrics, run scoring
- `observability-runtime`
  - trace, event log, replay assets, token accounting, query ledger

## 7. Graph Topology

### 7.1 Supervisor graph

`SupervisorGraph` is the top-level control graph.

It should only do the following:

- normalize incoming requests
- determine whether the request is single-capability or multi-capability
- dispatch work to one or more capability subgraphs
- coordinate serial and parallel execution
- collect outcome and evidence state from subgraphs
- trigger replan, fallback, or human-safe downgrade when needed
- produce the final response bundle and write-intent bundle

It must not become another giant business-logic graph.

### 7.2 Capability subgraphs

The kernel will include these specialized subgraphs:

- `TutorGraph`
- `DiagnoseGraph`
- `RecommendGraph`
- `PlanGraph`
- `ReviewGraph`
- `ProfileGraph`

Each subgraph owns one capability boundary and can evolve independently.

### 7.3 Node categories

To prevent the graph from collapsing into ad hoc code, nodes should be intentionally typed by responsibility:

- `Reasoning Nodes`
  - LLM-driven understanding, planning, explanation, critique, and synthesis
- `Tool Nodes`
  - controlled calls to business and retrieval tools
- `Guard Nodes`
  - evidence checks, risk checks, policy checks, and output validation
- `Deterministic Nodes`
  - normalization, state transformation, checkpoint packaging, and routing metadata
- `Control Nodes`
  - branching, retries, timeouts, degradation, and replan triggers

This makes the graph auditable and easier to evaluate.

## 8. Unified State Model

The unified kernel should use a durable structured state model instead of a loose in-memory dictionary.

Recommended state partitions:

- `RequestContext`
  - user identity, question context, submission context, exam and training context, conversation id, trace id
- `ExecutionState`
  - graph name, node pointer, retry counts, branch status, degradation status, timing, model-call metadata
- `WorkingMemory`
  - planner outputs, subgraph intermediate conclusions, candidate drafts, pending write intents
- `EvidenceState`
  - recalled candidates, reranked evidence, source list, evidence scores, coverage scores, trust labels
- `GuardrailState`
  - dirty-data markers, completeness checks, hallucination risk, policy outcomes, replan signals
- `OutcomeState`
  - final answer, recommendation package, plan draft, review report, profile update suggestion, write-intent payload

Every graph step should produce state deltas, not only plain text.

## 9. Persistence and Checkpointing

The agent kernel must be restart-safe and replayable.

Recommended persistence split:

- `RDS / MySQL`
  - run metadata
  - checkpoint metadata
  - final outputs
  - write-intent records
  - evaluation result records
- `Redis`
  - short-lived execution locks
  - token-rate limiting counters
  - idempotency keys
  - short-term cached execution state
- `OSS`
  - raw prompt and response snapshots
  - document parsing assets
  - retrieval replay artifacts
  - trace archives

Recommended checkpoint levels:

- `Run checkpoint`
  - stage-level recovery for the whole execution
- `Node checkpoint`
  - replay or restart from a critical node
- `Plan-step checkpoint`
  - fine-grained control for training-plan generation and validation

## 10. PlanGraph Design

`PlanGraph` is not a single-shot planner.

It should be a fully inspectable and repairable graph because the training plan is a long-lived business artifact.

Recommended stage flow:

- `Plan Intake`
  - receive user profile, recent submissions, exams, current goal, and operating constraints
- `Gap Analysis`
  - derive weaknesses, stable strengths, and conflict signals
- `Candidate Retrieval`
  - retrieve candidate questions, candidate training tasks, study materials, and stage-test options
- `Draft Planning`
  - use the large model to generate a structured plan draft
- `Plan Verification`
  - verify evidence support, task repetition, difficulty balance, profile consistency, and policy rules
- `Plan Repair`
  - repair or replan when verification fails
- `Execution Packaging`
  - package the final plan into write-intent payloads for Java services
- `Post-plan Evaluation Hook`
  - store evaluation inputs for offline regression and plan-quality analysis

This design allows later insertion of:

- process checks
- critic nodes
- human approval points
- policy gates
- quality scoring
- plan repair loops

## 11. Tool Runtime and Java/Python Boundary

The Python kernel should never bypass Java domain boundaries for business writes.

### 11.1 Tool classes

- `Read Tools`
  - question, submission, exam, training, profile, and recommendation-support reads
- `Retrieval Tools`
  - knowledge recall, evidence expansion, and similar-question retrieval
- `Write Intent Tools`
  - propose training-plan write, propose review write, propose profile update, propose recommendation packaging

### 11.2 Boundary rule

Python decides.

Java validates and persists.

This means:

- the agent can prepare write-intent payloads
- Java services perform final validation, authorization, transaction handling, and persistence
- failures in Java execution are surfaced back to the agent runtime as structured tool outcomes

This is necessary for production governance.

## 12. Retrieval Runtime

Retrieval must become a shared subsystem rather than scattered per-graph code.

### 12.1 Data split

- structured business data should be accessed through tools, not pseudo-RAG
- unstructured knowledge assets should go through a standard ingestion and indexing pipeline

### 12.2 Required sources in phase 1

- question data: title, statement, tags, difficulty, editorial and related metadata
- user submission data: code, verdicts, history, error patterns
- exam and training data: records, plans, tasks, completion state
- platform knowledge base: algorithm notes, tutorials, PDF material, operational documents
- user profile data: strengths, weaknesses, preferences, history-derived labels

### 12.3 Retrieval routes

Phase 1 should support at least four recall routes:

- `Structured Route`
  - exact business-entity lookups and filtered reads
- `Lexical Route`
  - BM25 or keyword retrieval for high-precision term matching
- `Dense Route`
  - semantic retrieval over vector indexes
- `Personalized Route`
  - user-profile-aware and history-aware additional recall

### 12.4 Fusion and reranking

Recall results should be fused and reranked before being injected into prompts.

Recommended sequence:

- route-local scoring
- cross-route fusion such as RRF or weighted score merge
- BGE reranker on the merged candidate pool
- deduplication and source-diversity control
- final evidence assembly

### 12.5 Evidence as a first-class object

Every retrieved item should be normalized into an `Evidence` object with:

- source type
- source id
- snippet
- source metadata
- recall score
- rerank score
- freshness
- trust label
- supported conclusion types

### 12.6 Dirty-data handling

The retrieval runtime must clean and mark bad data during ingestion and retrieval:

- encoding repair and mojibake isolation
- parsing-failure isolation
- metadata gap markers
- duplicate collapse
- stale-version filtering
- empty and noisy chunk filtering
- permission-based visibility control

### 12.7 Graph-ready retrieval flow

The retrieval subsystem should internally support a reusable retrieval graph:

- query normalization
- query rewrite or decomposition
- parallel multi-route recall
- fusion and rerank
- evidence sanity check
- context assembly

### 12.8 Evaluation hooks

Every retrieval run should persist enough artifacts to evaluate:

- original query
- rewritten query
- route candidates
- fused ranking
- reranked topK
- final evidence set

This enables retrieval metrics such as:

- Recall@K
- MRR
- nDCG
- Context Precision
- Evidence Coverage

## 13. Guardrail Runtime

The system requires a dedicated guardrail subsystem.

It should combine deterministic checks, smaller-model judgment, and graph-level repair loops.

### 13.1 Input guardrails

- request normalization
- dirty-data detection
- context completeness checks
- visibility and permission checks

### 13.2 Evidence guardrails

- evidence deduplication
- low-quality evidence filtering
- stale or conflicting evidence detection
- evidence coverage scoring
- task fit scoring

### 13.3 Output guardrails

- `Hard Checks`
  - entity existence, duplicate task prevention, payload completeness, hard business-rule checks
- `Soft Checks`
  - small-model risk scoring for unsupported conclusions, weak plan quality, profile inconsistency, and answer drift
- `Policy Checks`
  - no direct AC-code leakage, no over-broad claims, no unauthorized data access, no unsafe write proposals

### 13.4 Risk handling

- `Low risk`
  - local repair or re-retrieval
- `Medium risk`
  - graph-level revise or replan
- `High risk`
  - safe downgrade or escalation path
- `Write risk`
  - hold or reject write-intent generation until validation passes

## 14. Model Topology

The accepted model topology for phase 1 is:

- one larger generation model
- one smaller verification and risk model
- one BGE reranker for retrieval ranking improvement

Recommended responsibility split:

- `Large model`
  - planning, explanation, synthesis, recommendation, review generation
- `Small model`
  - critic, verifier, hallucination-risk scoring, evidence-fit scoring, output safety scoring
- `BGE reranker`
  - improve topK evidence quality after multi-route recall

This reduces self-confirmation bias and improves cost control.

## 15. Observability Runtime

Observability should be designed for production operations and replay, not only logs.

### 15.1 Trace model

- `Run Trace`
  - one end-to-end request or task execution trace
- `Node Trace`
  - one graph-node execution record
- `Tool Trace`
  - one tool call record

### 15.2 Required online fields

- `trace_id`, `run_id`, `conversation_id`, `user_id`
- graph name, node name, task type
- model and reranker identities
- token usage and time cost
- retrieval route and rerank outcomes
- guardrail outcome and fallback type
- final response type and write-intent type

### 15.3 Query ledger

Maintain an auditable query ledger that records:

- user request
- graph path
- accessed tools and knowledge sources
- final evidence package
- output category
- retries, downgrade, or human-safe fallback
- total token and latency cost

## 16. Evaluation Runtime

Evaluation must be built as a submission-safe and iteration-safe regression system.

### 16.1 Online quality signals

- explicit user feedback
- implicit task acceptance and follow-up behavior
- degradation and retry rates
- write-intent acceptance rates

### 16.2 Offline evaluation groups

- `Intent and routing`
  - route correctness and subgraph selection correctness
- `Retrieval`
  - Recall@K, MRR, Context Precision, Evidence Coverage, reranker benefit
- `Generation`
  - evidence grounding, completeness, hallucination rate, policy compliance
- `Planning`
  - executability, profile consistency, difficulty balance, duplication rate, historical-fit quality

### 16.3 Special context metrics

Phase 1 should explicitly support:

- `Context Precision Test`
  - how much of the final prompt context directly supports the outcome
- `Context Sufficiency Test`
  - whether the final context was sufficient for a trustworthy answer or plan

### 16.4 CI and post-commit evaluation

Every important agent change should trigger:

- graph and runtime tests
- retrieval regression tests
- answer and plan evaluation sets
- trend report output with changed metrics and failed examples

## 17. Runtime Stability Controls

The kernel should enforce runtime stability at the agent level, not only at the gateway.

### 17.1 Rate and budget controls

- user-level rate limits
- graph-level concurrency limits
- model-level token and request budgets
- reranker and retrieval fan-out limits

### 17.2 Degradation ladder

When the system is overloaded or budget constrained, degrade in this order:

- shorten context length
- reduce rerank candidate count
- switch to lighter execution mode
- queue or reject only as the last step

## 18. Infrastructure and Deployment

### 18.1 Deployment topology

- `Judge`
  - separate small server because it binds to execution sandbox requirements
- `SAE stateless services`
  - `agent-runtime`
  - gateway-facing Python services if split later
  - supporting stateless ingestion and evaluation workers if needed
- `Managed middleware`
  - RDS MySQL
  - Redis
  - MQ
  - OSS
  - OpenSearch or Elasticsearch
  - vector retrieval service or managed vector capability

### 18.2 Phase-1 database stance

Phase 1 intentionally does not require Neo4j or GraphRAG as a hard dependency.

However, the retrieval runtime should leave a future extension point for a later `Graph Route`.

## 19. Phase-1 Deliverables

Phase 1 of this redesign should deliver:

- unified Python `agent-runtime`
- `SupervisorGraph`
- six capability subgraphs with clear boundaries
- `PlanGraph` redesigned as a graph-native, verifiable planning flow
- shared retrieval runtime with lexical + dense + personalized recall and BGE reranking
- shared guardrail runtime with deterministic checks and small-model verification
- shared tool runtime with strong Java/Python contracts
- persistent execution state, run records, and checkpoint support
- online trace, query ledger, token accounting, and replay assets
- automated evaluation pipeline and regression metrics

## 20. Future Extensions

The architecture should leave deliberate room for later additions:

- graph database route and GraphRAG
- Text2Cypher and structured graph exploration
- human approval workflows for specific write intents
- richer planner and critic multi-agent patterns
- more advanced domain-specific evaluation suites
- stronger adaptive routing and personalized retrieval weighting

## 21. Success Criteria

The redesign is successful when SynCode can truthfully claim:

- the agent kernel is graph-native rather than post-hoc wrapped
- planning and tutoring both run on durable, inspectable execution state
- retrieval is multi-route, reranked, and traceable
- outputs are guarded by deterministic checks and independent model verification
- every important run is replayable, measurable, and regressible
- Java and Python responsibilities stay clean and production-safe

