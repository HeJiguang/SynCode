from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path

from sqlalchemy import create_engine
from fastapi import HTTPException
import pytest
import yaml

import app.mcp_gateway.server as gateway_server
from app.mcp_gateway.identity import ToolIdentityError, user_id_from_profile
from app.mcp_gateway.profiles import HermesProfileProvisioner, ProfileProvisionError
from app.mcp_gateway.repository import LearningRepository
from app.mcp_gateway.server import mcp, record_skill_events
from app.skill_governance.usage import SkillUsageBatch, SkillUsageEvent, SkillUsageRepository


def _repository(tmp_path) -> LearningRepository:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'learning.sqlite3'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE tb_question (question_id INTEGER PRIMARY KEY, title TEXT, difficulty INTEGER, "
            "algorithm_tag TEXT, knowledge_tags TEXT, estimated_minutes INTEGER, training_enabled INTEGER, "
            "time_limit INTEGER, space_limit INTEGER, content TEXT, default_code TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_user_submit (submit_id INTEGER PRIMARY KEY, user_id INTEGER, question_id INTEGER, "
            "program_type INTEGER, user_code TEXT, pass INTEGER, score INTEGER, exe_message TEXT, "
            "case_judge_res TEXT, use_time INTEGER, use_memory INTEGER, judge_status INTEGER, "
            "create_time TEXT, update_time TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_training_profile (user_id INTEGER, current_level TEXT, target_direction TEXT, "
            "weak_points TEXT, strong_points TEXT, last_test_exam_id INTEGER, last_plan_id INTEGER, status INTEGER)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_training_plan (plan_id INTEGER PRIMARY KEY, user_id INTEGER, plan_title TEXT, "
            "plan_goal TEXT, source_type TEXT, based_on_exam_id INTEGER, plan_status INTEGER, ai_summary TEXT, "
            "create_time TEXT, update_time TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_training_task (task_id INTEGER PRIMARY KEY, plan_id INTEGER, user_id INTEGER, "
            "task_type TEXT, question_id INTEGER, exam_id INTEGER, title_snapshot TEXT, task_order INTEGER, "
            "task_status INTEGER, recommended_reason TEXT, knowledge_tags_snapshot TEXT, due_time TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO tb_question VALUES (101, 'Two Sum', 1, 'hash', 'array,hash', 20, 1, 1000, 128, "
            "'Find two numbers', 'class Solution {}')"
        )
        connection.exec_driver_sql(
            "INSERT INTO tb_question VALUES (102, 'Binary Search', 1, 'binary search', 'array', 15, 1, 1000, 128, "
            "'Find a target', 'class Solution {}')"
        )
        connection.exec_driver_sql(
            "INSERT INTO tb_user_submit VALUES (1, 7, 101, 0, 'code', 0, 0, 'wrong answer', '{}', 4, 10, 1, "
            "'2026-01-01', NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO tb_training_profile VALUES (7, 'starter', 'algorithms', 'hash map', 'loops', NULL, NULL, 1)"
        )
    engine.dispose()
    return LearningRepository(database_url)


def test_production_schema_readiness_requires_every_agent_table():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        ready, message = gateway_server._database_schema_check(engine)
        assert ready is False
        assert "database schema unavailable" in message
        with engine.begin() as connection:
            for table in gateway_server._PRODUCTION_TABLES:
                connection.exec_driver_sql(f"CREATE TABLE `{table}` (id INTEGER)")
        assert gateway_server._database_schema_check(engine) == (
            True,
            "database schema ready",
        )
    finally:
        engine.dispose()


def test_profile_identity_is_strict():
    assert user_id_from_profile("syncode-u123") == "123"
    for invalid in ("syncode-u", "syncode-u1/../2", "alice", "syncode-u-1"):
        try:
            user_id_from_profile(invalid)
        except ToolIdentityError:
            pass
        else:
            raise AssertionError(f"invalid profile accepted: {invalid}")


def test_mcp_exposes_memory_evidence_details_but_not_core_recall_entrypoints():
    tools = asyncio.run(mcp.get_tools())
    assert {
        "get_my_learning_memory_detail",
        "get_my_learning_state_memory_detail",
    }.issubset(tools)
    assert "recall_my_learning_memory" not in tools
    assert "recall_my_learning_state_memory" not in tools


def test_read_only_learning_queries_are_scoped(tmp_path):
    repository = _repository(tmp_path)
    try:
        question = repository.get_question("101")
        assert question and question["title"] == "Two Sum"
        assert repository.get_submission_history("7", "101")[0]["exe_message"] == "wrong answer"
        assert repository.get_submission_history("8", "101") == []
        profile = repository.get_learning_profile("7")
        assert profile["submission_count"] == 1
        assert profile["training_profile"]["weak_points"] == "hash map"
        suggestions = repository.search_practice_questions("7", knowledge_tag="array")
        assert [item["question_id"] for item in suggestions] == [101, 102]
    finally:
        repository.close()


def _profile_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    monkeypatch.setenv("HERMES_API_SERVER_KEY", "hermes-api-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("SYNCODE_MCP_SERVICE_KEY", "mcp-key")
    monkeypatch.setenv("SYNCODE_HERMES_SKILLS_DIR", "/opt/syncode/hermes/skills")
    monkeypatch.setenv("SYNCODE_MCP_PUBLIC_URL", "http://oj-agent-tools:8016/mcp")
    monkeypatch.setenv(
        "SYNCODE_HERMES_MEMORY_PROVIDER_DIR",
        str(Path(__file__).parents[2] / "hermes" / "plugins" / "syncode-learning-memory"),
    )


def test_profile_provisioning_is_idempotent_and_scoped(monkeypatch, tmp_path):
    _profile_environment(monkeypatch, tmp_path)
    provisioner = HermesProfileProvisioner()

    assert provisioner.ensure(user_id="7", profile="syncode-u7") is True
    assert provisioner.ensure(user_id="7", profile="syncode-u7") is False

    profile_dir = tmp_path / "hermes" / "profiles" / "syncode-u7"
    config = yaml.safe_load((profile_dir / "config.yaml").read_text(encoding="utf-8"))
    assert config["platform_toolsets"]["api_server"] == ["memory", "syncode"]
    assert config["memory"] == {
        "provider": "syncode-learning-memory",
        "syncode-learning-memory": {
            "endpoint": "http://oj-agent-tools:8016/internal/learning-memory/recall",
            "timeout_seconds": 4.0,
        },
    }
    assert config["mcp_servers"]["syncode"]["trust"] == "untrusted"
    assert config["mcp_servers"]["syncode"]["identity_header"] == {
        "name": "X-SynCode-Hermes-Profile",
        "value_from": "profile",
    }
    assert (profile_dir / ".env").stat().st_mode & 0o777 == 0o600
    assert (profile_dir / "config.yaml").stat().st_mode & 0o777 == 0o600
    assert (profile_dir / "plugins" / "syncode-learning-memory" / "__init__.py").is_file()


def test_core_learning_memory_context_uses_profile_scoped_user_and_related_tags(monkeypatch):
    calls: list[tuple[str, str, object]] = []

    class ProblemMemory:
        def recall(self, **kwargs):
            calls.append(("problem", kwargs["user_id"], kwargs["query"]))
            return {
                "patterns": [],
                "episodes": [{"knowledge_tags": ["binary-search", "array"]}],
                "events": [{"knowledge_tags": ["array"]}],
            }

    class StateMemory:
        def recall(self, **kwargs):
            calls.append(("state", kwargs["user_id"], kwargs["knowledge_tags"]))
            return {"states": []}

    monkeypatch.setattr(gateway_server, "_learning_memory_service", ProblemMemory())
    monkeypatch.setattr(gateway_server, "_learning_state_service", StateMemory())
    result = gateway_server._build_learning_memory_context(user_id="7", query="二分为什么超时")

    assert result["memory_domain"] == "syncode_learning"
    assert calls == [
        ("problem", "7", "二分为什么超时"),
        ("state", "7", ["binary-search", "array"]),
    ]


def test_core_learning_memory_identity_is_derived_from_profile(monkeypatch):
    monkeypatch.setenv("SYNCODE_MCP_SERVICE_KEY", "memory-key")
    assert gateway_server._resolve_learning_memory_identity(
        "Bearer memory-key", "syncode-u42"
    ) == "42"
    with pytest.raises(HTTPException):
        gateway_server._resolve_learning_memory_identity(
            "Bearer memory-key", "syncode-u43/../42"
        )


def test_profile_provisioning_is_atomic_under_concurrency(monkeypatch, tmp_path):
    _profile_environment(monkeypatch, tmp_path)

    def ensure() -> bool:
        return HermesProfileProvisioner().ensure(user_id="9", profile="syncode-u9")

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _index: ensure(), range(8)))

    assert results.count(True) == 1
    assert results.count(False) == 7
    target = tmp_path / "hermes" / "profiles" / "syncode-u9"
    assert HermesProfileProvisioner._is_complete(target)
    assert not list(target.parent.glob(".syncode-u9-*"))


def test_profile_provisioning_rejects_cross_user_profile(monkeypatch, tmp_path):
    _profile_environment(monkeypatch, tmp_path)
    try:
        HermesProfileProvisioner().ensure(user_id="7", profile="syncode-u8")
    except ProfileProvisionError:
        pass
    else:
        raise AssertionError("cross-user Hermes profile was accepted")


def test_skill_telemetry_is_versioned_and_idempotent(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'telemetry.sqlite3'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE tb_ai_skill (skill_id TEXT PRIMARY KEY, skill_name TEXT, scope TEXT, "
            "owner_user_id INTEGER, lifecycle_status TEXT, current_version TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO tb_ai_skill VALUES "
            "('platform:syncode-diagnosis', 'syncode-diagnosis', 'platform', 0, 'active', '1.2.0')"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_ai_skill_usage_event (event_id TEXT PRIMARY KEY, user_id INTEGER, "
            "profile_name TEXT, run_id TEXT, correlation_id TEXT, session_id TEXT, skill_name TEXT, skill_version TEXT, "
            "question_id INTEGER, event_type TEXT, occurred_at TEXT, payload_json TEXT, create_time TEXT)"
        )
    engine.dispose()

    event = SkillUsageEvent(
        event_id="run-1:skill-view",
        event_type="skill.invoked",
        occurred_at=datetime(2026, 10, 14, tzinfo=timezone.utc),
        run_id="run-1",
        session_id="session-1",
        skill_name="syncode-diagnosis",
        payload={"tool": "skill_view"},
    )
    telemetry = SkillUsageRepository(database_url)
    try:
        assert telemetry.record_events(user_id="7", profile="syncode-u7", events=[event]) == (1, 0)
        assert telemetry.record_events(user_id="7", profile="syncode-u7", events=[event]) == (0, 1)
        with telemetry.engine.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT skill_version, payload_json FROM tb_ai_skill_usage_event"
            ).mappings().one()
        assert row["skill_version"] == "1.2.0"
        assert json.loads(row["payload_json"]) == {"tool": "skill_view"}
    finally:
        telemetry.close()


def test_skill_telemetry_rejects_cross_user_profile(tmp_path):
    telemetry = SkillUsageRepository(f"sqlite+pysqlite:///{tmp_path / 'telemetry.sqlite3'}")
    event = SkillUsageEvent(
        event_id="run-1:skill-view",
        event_type="skill.invoked",
        occurred_at=datetime.now(timezone.utc),
        run_id="run-1",
        skill_name="loop-helper",
    )
    try:
        with pytest.raises(ValueError, match="identity"):
            telemetry.record_events(user_id="7", profile="syncode-u8", events=[event])
    finally:
        telemetry.close()


def test_internal_skill_telemetry_endpoint_authenticates_and_scopes(monkeypatch):
    event = SkillUsageEvent(
        event_id="run-1:skill-view",
        event_type="skill.invoked",
        occurred_at=datetime.now(timezone.utc),
        run_id="run-1",
        skill_name="loop-helper",
    )
    batch = SkillUsageBatch(user_id="7", profile="syncode-u7", events=[event])

    class StubRepository:
        def record_events(self, **kwargs):
            assert kwargs == {"user_id": "7", "profile": "syncode-u7", "events": [event]}
            return 1, 0

    monkeypatch.setenv("SYNCODE_HERMES_PROVISION_KEY", "telemetry-key")
    monkeypatch.setattr("app.mcp_gateway.server.usage_repository", lambda: StubRepository())
    assert record_skill_events(batch, "Bearer telemetry-key") == {
        "accepted": 1,
        "duplicates": 0,
    }

    with pytest.raises(HTTPException) as unauthorized:
        record_skill_events(batch, "Bearer wrong-key")
    assert unauthorized.value.status_code == 401

    mismatched = SkillUsageBatch(user_id="7", profile="syncode-u8", events=[event])
    with pytest.raises(HTTPException) as invalid:
        record_skill_events(mismatched, "Bearer telemetry-key")
    assert invalid.value.status_code == 400
