from pathlib import Path

from app.observability.query_ledger import QueryLedger, QueryLedgerEntry
from app.observability.trace import InMemoryTraceStore, NodeTraceEvent, RunTrace


def test_in_memory_trace_store_records_run_and_node_events():
    store = InMemoryTraceStore()
    run = RunTrace(
        trace_id="trace-001",
        run_id="run-001",
        graph_name="llm_runtime",
        task_type="chat",
        user_id="u-1",
    )

    store.record_run(run)
    store.record_node_event(
        NodeTraceEvent(
            trace_id="trace-001",
            run_id="run-001",
            graph_name="llm_runtime",
            node_name="response_packaging",
            status="succeeded",
        )
    )

    assert store.get_run("run-001").graph_name == "llm_runtime"
    assert store.list_node_events("run-001")[0].node_name == "response_packaging"


def test_query_ledger_records_query_summary():
    ledger = QueryLedger()
    entry = QueryLedgerEntry(
        trace_id="trace-002",
        run_id="run-002",
        user_id="u-2",
        task_type="training_plan",
        request_text="Generate my next training plan.",
        graph_path=["llm_runtime", "training_plan_llm"],
        evidence_sources=["doc-1", "question-101"],
        output_type="plan_response",
        token_cost=123,
        latency_ms=456,
    )

    ledger.append(entry)

    assert ledger.list_entries()[0].output_type == "plan_response"
    assert ledger.list_entries()[0].token_cost == 123


def test_trace_store_can_use_custom_repository():
    class _StubTraceRepository:
        def __init__(self):
            self.runs = {}
            self.events = {}

        def record_run(self, run):
            self.runs[run.run_id] = run

        def record_node_event(self, event):
            self.events.setdefault(event.run_id, []).append(event)

        def get_run(self, run_id):
            return self.runs[run_id]

        def list_node_events(self, run_id):
            return list(self.events.get(run_id, []))

        def clear(self):
            self.runs.clear()
            self.events.clear()

    repository = _StubTraceRepository()
    store = InMemoryTraceStore(repository=repository)
    run = RunTrace(
        trace_id="trace-003",
        run_id="run-003",
        graph_name="llm_runtime",
        task_type="diagnosis",
        user_id="u-3",
    )

    store.record_run(run)

    assert repository.get_run("run-003").graph_name == "llm_runtime"


def test_query_ledger_can_use_custom_repository():
    class _StubLedgerRepository:
        def __init__(self):
            self.entries = []

        def append(self, entry):
            self.entries.append(entry)

        def list_entries(self):
            return list(self.entries)

        def clear(self):
            self.entries.clear()

    repository = _StubLedgerRepository()
    ledger = QueryLedger(repository=repository)
    entry = QueryLedgerEntry(
        trace_id="trace-004",
        run_id="run-004",
        user_id="u-4",
        task_type="review",
        request_text="Summarize my recent practice.",
        graph_path=["llm_runtime", "response_packaging"],
        evidence_sources=[],
        output_type="review_summary",
    )

    ledger.append(entry)

    assert repository.list_entries()[0].output_type == "review_summary"


def test_jsonl_trace_repository_persists_runs_and_events(tmp_path):
    from app.observability.repositories.file_trace_repository import JsonlTraceRepository  # noqa: WPS433

    repository = JsonlTraceRepository(tmp_path)
    run = RunTrace(
        trace_id="trace-file-001",
        run_id="run-file-001",
        graph_name="llm_runtime",
        task_type="chat",
        user_id="u-file",
    )
    event = NodeTraceEvent(
        trace_id="trace-file-001",
        run_id="run-file-001",
        graph_name="llm_runtime",
        node_name="response_packaging",
        status="succeeded",
    )

    repository.record_run(run)
    repository.record_node_event(event)

    assert repository.get_run("run-file-001").task_type == "chat"
    assert repository.list_node_events("run-file-001")[0].node_name == "response_packaging"
    assert (tmp_path / "trace-runs.jsonl").exists()
    assert (tmp_path / "trace-node-events.jsonl").exists()


def test_jsonl_query_ledger_repository_persists_entries(tmp_path):
    from app.observability.repositories.file_query_ledger_repository import JsonlQueryLedgerRepository  # noqa: WPS433

    repository = JsonlQueryLedgerRepository(tmp_path)
    entry = QueryLedgerEntry(
        trace_id="trace-file-002",
        run_id="run-file-002",
        user_id="u-file",
        task_type="review",
        request_text="Summarize my practice.",
        graph_path=["llm_runtime", "response_packaging"],
        evidence_sources=["doc-1"],
        output_type="review_summary",
        token_cost=18,
        latency_ms=52,
    )

    repository.append(entry)

    assert repository.list_entries()[0].graph_path == ["llm_runtime", "response_packaging"]
    assert (tmp_path / "query-ledger.jsonl").exists()


def test_build_default_trace_store_can_use_file_repository(monkeypatch, tmp_path):
    import app.observability.trace as trace_module  # noqa: WPS433

    monkeypatch.setenv("OJ_AGENT_TRACE_STORE", "file")
    monkeypatch.setenv("OJ_AGENT_RUNTIME_DATA_DIR", str(tmp_path))

    store = trace_module.build_default_trace_store()
    run = RunTrace(
        trace_id="trace-file-003",
        run_id="run-file-003",
        graph_name="llm_runtime",
        task_type="diagnosis",
        user_id="u-file",
    )

    store.record_run(run)

    assert store.get_run("run-file-003").task_type == "diagnosis"
    assert (Path(tmp_path) / "trace-runs.jsonl").exists()
