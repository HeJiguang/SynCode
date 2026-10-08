from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine
import yaml

from app.mcp_gateway.identity import ToolIdentityError, user_id_from_profile
from app.mcp_gateway.profiles import HermesProfileProvisioner, ProfileProvisionError
from app.mcp_gateway.repository import LearningRepository


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


def test_profile_provisioning_is_idempotent_and_scoped(monkeypatch, tmp_path):
    _profile_environment(monkeypatch, tmp_path)
    provisioner = HermesProfileProvisioner()

    assert provisioner.ensure(user_id="7", profile="syncode-u7") is True
    assert provisioner.ensure(user_id="7", profile="syncode-u7") is False

    profile_dir = tmp_path / "hermes" / "profiles" / "syncode-u7"
    config = yaml.safe_load((profile_dir / "config.yaml").read_text(encoding="utf-8"))
    assert config["platform_toolsets"]["api_server"] == ["memory", "syncode"]
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


def test_profile_provisioning_rejects_cross_user_profile(monkeypatch, tmp_path):
    _profile_environment(monkeypatch, tmp_path)
    try:
        HermesProfileProvisioner().ensure(user_id="7", profile="syncode-u8")
    except ProfileProvisionError:
        pass
    else:
        raise AssertionError("cross-user Hermes profile was accepted")
