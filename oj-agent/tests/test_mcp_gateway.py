from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine
import yaml

from app.mcp_gateway.identity import ToolIdentityError, user_id_from_profile
from app.mcp_gateway.profiles import HermesProfileProvisioner, ProfileProvisionError
from app.mcp_gateway.repository import LearningRepository
from app.mcp_gateway.server import mcp


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
            "CREATE TABLE tb_training_profile (profile_id INTEGER PRIMARY KEY, user_id INTEGER, "
            "current_level TEXT, target_direction TEXT, weak_points TEXT, strong_points TEXT, "
            "last_test_exam_id INTEGER, last_plan_id INTEGER, status INTEGER, create_by INTEGER, "
            "create_time TEXT, update_by INTEGER, update_time TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_training_plan (plan_id INTEGER PRIMARY KEY, user_id INTEGER, plan_title TEXT, "
            "plan_goal TEXT, source_type TEXT, based_on_exam_id INTEGER, plan_status INTEGER, ai_summary TEXT, "
            "create_by INTEGER, create_time TEXT, update_by INTEGER, update_time TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_training_task (task_id INTEGER PRIMARY KEY, plan_id INTEGER, user_id INTEGER, "
            "task_type TEXT, question_id INTEGER, exam_id INTEGER, title_snapshot TEXT, task_order INTEGER, "
            "task_status INTEGER, recommended_reason TEXT, knowledge_tags_snapshot TEXT, due_time TEXT, "
            "create_by INTEGER, create_time TEXT, update_by INTEGER, update_time TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_ai_recommendation_event (event_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, recommendation_id TEXT NOT NULL, action TEXT NOT NULL, "
            "question_id INTEGER, plan_id INTEGER, task_id INTEGER, run_id TEXT, metadata_json TEXT NOT NULL, "
            "create_time TEXT NOT NULL)"
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
            "INSERT INTO tb_question VALUES (103, 'Disabled', 1, 'array', 'array', 10, 0, 1000, 128, "
            "'Unavailable', 'class Solution {}')"
        )
        connection.exec_driver_sql(
            "INSERT INTO tb_user_submit VALUES (1, 7, 101, 0, 'code', 0, 0, 'wrong answer', '{}', 4, 10, 1, "
            "'2026-01-01', NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO tb_training_profile VALUES (7001, 7, 'starter', 'algorithms', 'hash map', 'loops', "
            "NULL, NULL, 1, 7, '2026-01-01', 7, '2026-01-01')"
        )
    engine.dispose()
    return LearningRepository(database_url)


def test_profile_identity_is_strict():
    assert user_id_from_profile("syncode-u123") == "123"
    for invalid in ("syncode-u", "syncode-u1/../2", "alice", "syncode-u-1"):
        try:
            user_id_from_profile(invalid)
        except ToolIdentityError:
            pass
        else:
            raise AssertionError(f"invalid profile accepted: {invalid}")


def test_read_only_learning_queries_are_scoped(tmp_path):
    repository = _repository(tmp_path)
    try:
        question = repository.get_question("101")
        assert question and question["title"] == "Two Sum"
        assert repository.get_submission_history("7", "101")[0]["exe_message"] == "wrong answer"
        assert repository.get_submission_history("8", "101") == []
        recent = repository.get_recent_submissions("7")
        assert recent[0]["title"] == "Two Sum"
        assert "user_code" not in recent[0]
        assert repository.get_recent_submissions("8") == []
        sources = repository.list_learning_profile_sources()
        assert sources == [
            {"user_id": "7", "source_watermark": "1:1:2026-01-01"}
        ]
        profile = repository.get_learning_profile("7")
        assert profile["submission_count"] == 1
        assert profile["training_profile"]["weak_points"] == "hash map"
        suggestions = repository.search_practice_questions("7", knowledge_tag="array")
        assert [item["question_id"] for item in suggestions] == [101, 102]
    finally:
        repository.close()


def test_training_plan_write_and_effect_tracking_are_user_scoped(tmp_path):
    repository = _repository(tmp_path)
    try:
        plan = repository.save_training_plan(
            "7",
            plan_title="Array recovery",
            plan_goal="Pass both array exercises",
            tasks=[
                {"question_id": "101", "recommended_reason": "Retry the failed hash-map case."},
                {"question_id": "102", "recommended_reason": "Practice a boundary-safe binary search."},
            ],
            ai_summary="A short plan approved by the learner.",
        )
        assert plan["source_type"] == "hermes_agent"
        assert [task["question_id"] for task in plan["tasks"]] == [101, 102]
        assert all(task["task_id"] for task in plan["tasks"])

        first_task = str(plan["tasks"][0]["task_id"])
        with pytest.raises(KeyError):
            repository.update_training_task("8", first_task, 1)
        updated = repository.update_training_task("7", first_task, 1)
        assert updated["task_status"] == 1
        assert updated["plan_completed"] is False

        with repository.engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO tb_user_submit VALUES (2, 7, 101, 0, 'fixed', 1, 100, 'accepted', '{}', "
                "3, 9, 2, '2099-01-01', '2099-01-01')"
            )
        effects = repository.get_training_effects("7", str(plan["plan_id"]))
        assert effects["summary"] == {
            "task_count": 2,
            "completed_tasks": 1,
            "skipped_tasks": 0,
            "passed_questions": 1,
            "attempts": 1,
        }
        assert effects["tasks"][0]["effect"]["best_score"] == 100

        with repository.engine.connect() as connection:
            events = connection.exec_driver_sql(
                "SELECT action, user_id, plan_id, task_id FROM tb_ai_recommendation_event ORDER BY event_id"
            ).all()
        assert [row[0] for row in events] == ["accepted", "accepted", "completed"]
        assert {row[1] for row in events} == {7}
        assert all(row[2] == plan["plan_id"] for row in events)
    finally:
        repository.close()


def test_training_plan_rejects_duplicate_or_unavailable_questions(tmp_path):
    repository = _repository(tmp_path)
    try:
        with pytest.raises(ValueError, match="duplicate"):
            repository.save_training_plan(
                "7",
                plan_title="Duplicate",
                plan_goal="Should fail",
                tasks=[
                    {"question_id": "101", "recommended_reason": "one"},
                    {"question_id": "101", "recommended_reason": "two"},
                ],
            )
        with pytest.raises(ValueError, match="not available"):
            repository.save_training_plan(
                "7",
                plan_title="Unavailable",
                plan_goal="Should fail",
                tasks=[{"question_id": "103", "recommended_reason": "disabled"}],
            )
        assert repository.get_current_training_plan("7") is None
    finally:
        repository.close()


def test_recommendation_feedback_is_persisted_and_validated(tmp_path):
    repository = _repository(tmp_path)
    try:
        recorded = repository.record_recommendation_feedback(
            "7",
            recommendation_id="run-7-question-102",
            action="opened",
            question_id="102",
            run_id="rtr.runtime-a.example",
        )
        assert recorded["event_id"] > 0
        with repository.engine.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT user_id, recommendation_id, action, question_id, run_id "
                "FROM tb_ai_recommendation_event WHERE event_id = ?",
                (recorded["event_id"],),
            ).one()
        assert tuple(row) == (7, "run-7-question-102", "opened", 102, "rtr.runtime-a.example")
        with pytest.raises(ValueError, match="does not exist"):
            repository.record_recommendation_feedback(
                "7", recommendation_id="bad", action="opened", question_id="999"
            )
    finally:
        repository.close()


def test_mcp_write_tools_are_declared_non_read_only():
    tools = mcp._tool_manager._tools
    for name in (
        "save_my_training_plan",
        "update_my_training_task",
        "record_my_recommendation_feedback",
    ):
        assert tools[name].annotations.readOnlyHint is False
    assert tools["get_my_training_effects"].annotations.readOnlyHint is True
    assert tools["get_my_recent_submissions"].annotations.readOnlyHint is True


def _profile_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    monkeypatch.setenv("HERMES_API_SERVER_KEY", "hermes-api-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("SYNCODE_MCP_SERVICE_KEY", "mcp-key")
    monkeypatch.setenv("SYNCODE_HERMES_SKILLS_DIR", "/opt/syncode/hermes/skills")
    monkeypatch.setenv("SYNCODE_MCP_PUBLIC_URL", "http://oj-agent-tools:8016/mcp")


def test_profile_provisioning_is_idempotent_and_scoped(monkeypatch, tmp_path):
    _profile_environment(monkeypatch, tmp_path)
    provisioner = HermesProfileProvisioner()

    assert provisioner.ensure(user_id="7", profile="syncode-u7") is True
    assert provisioner.ensure(user_id="7", profile="syncode-u7") is False

    profile_dir = tmp_path / "hermes" / "profiles" / "syncode-u7"
    config = yaml.safe_load((profile_dir / "config.yaml").read_text(encoding="utf-8"))
    assert config["platform_toolsets"]["api_server"] == ["memory", "syncode"]
    assert config["memory"] == {
        "memory_enabled": True,
        "user_profile_enabled": True,
        "write_approval": True,
    }
    assert config["context"] == {"engine": "syncode_reviewed"}
    assert config["mcp_servers"]["syncode"]["trust"] == "untrusted"
    assert config["mcp_servers"]["syncode"]["identity_header"] == {
        "name": "X-SynCode-Hermes-Profile",
        "value_from": "profile",
    }
    assert (profile_dir / ".env").stat().st_mode & 0o777 == 0o600
    assert (profile_dir / "config.yaml").stat().st_mode & 0o777 == 0o600


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


def test_profile_provisioning_migrates_existing_config_without_losing_unknown_settings(monkeypatch, tmp_path):
    _profile_environment(monkeypatch, tmp_path)
    provisioner = HermesProfileProvisioner()
    assert provisioner.ensure(user_id="11", profile="syncode-u11") is True
    config_path = tmp_path / "hermes" / "profiles" / "syncode-u11" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["memory"] = {"memory_char_limit": 3000}
    config["custom_setting"] = {"keep": True}
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    assert provisioner.ensure(user_id="11", profile="syncode-u11") is False
    migrated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert migrated["memory"]["write_approval"] is True
    assert migrated["memory"]["memory_char_limit"] == 3000
    assert migrated["custom_setting"] == {"keep": True}
    assert config_path.stat().st_mode & 0o777 == 0o600


def test_profile_provisioning_rejects_cross_user_profile(monkeypatch, tmp_path):
    _profile_environment(monkeypatch, tmp_path)
    try:
        HermesProfileProvisioner().ensure(user_id="7", profile="syncode-u8")
    except ProfileProvisionError:
        pass
    else:
        raise AssertionError("cross-user Hermes profile was accepted")
