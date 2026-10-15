from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine

from app.learning_memory.projector import project_learning_memories
from app.learning_memory.repository import LearningMemoryRepository
from app.learning_memory.service import LearningMemoryService
from app.learning_memory.state_projector import project_learning_states
from app.learning_memory.state_service import LearningStateService


class DisabledMemoryIndex:
    enabled = False


def _database(tmp_path) -> str:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'learning-memory.sqlite3'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE tb_question (question_id INTEGER PRIMARY KEY, title TEXT, difficulty INTEGER, "
            "algorithm_tag TEXT, knowledge_tags TEXT, update_time TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_user_submit (submit_id INTEGER PRIMARY KEY, user_id INTEGER, question_id INTEGER, "
            "exam_id INTEGER, program_type INTEGER, user_code TEXT, pass INTEGER, score INTEGER, "
            "exe_message TEXT, use_time INTEGER, use_memory INTEGER, judge_status INTEGER, last_error TEXT, "
            "finish_time TEXT, create_time TEXT, update_time TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_exam (exam_id INTEGER PRIMARY KEY, title TEXT, end_time TEXT, update_time TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE tb_user_exam (user_exam_id INTEGER PRIMARY KEY, user_id INTEGER, exam_id INTEGER, "
            "score INTEGER, exam_rank INTEGER, create_time TEXT, update_time TEXT)"
        )
        connection.exec_driver_sql(
            """CREATE TABLE tb_ai_learning_memory (
                memory_id TEXT PRIMARY KEY, user_id INTEGER, memory_level TEXT, memory_type TEXT,
                title TEXT, summary TEXT, knowledge_tags_json TEXT, error_type TEXT,
                memory_status TEXT, confidence REAL, occurrence_count INTEGER, source_type TEXT,
                source_id TEXT, occurred_at TEXT, first_seen_at TEXT, last_seen_at TEXT,
                content_hash TEXT, structured_payload TEXT, create_time TEXT, update_time TEXT)"""
        )
        connection.exec_driver_sql(
            """CREATE TABLE tb_ai_learning_memory_evidence (
                memory_id TEXT, evidence_type TEXT, evidence_id TEXT, occurred_at TEXT,
                snippet TEXT, structured_payload TEXT, create_time TEXT,
                PRIMARY KEY(memory_id, evidence_type, evidence_id))"""
        )
        connection.exec_driver_sql(
            """CREATE TABLE tb_ai_learning_memory_projection_state (
                user_id INTEGER PRIMARY KEY, source_fingerprint TEXT, event_count INTEGER,
                episode_count INTEGER, pattern_count INTEGER, indexed_fingerprint TEXT,
                last_sync_at TEXT, last_indexed_at TEXT, create_time TEXT, update_time TEXT)"""
        )
        connection.exec_driver_sql(
            """CREATE TABLE tb_ai_learning_state_memory (
                state_id TEXT PRIMARY KEY, user_id INTEGER, knowledge_tag TEXT, mastery_level TEXT,
                mastery_score REAL, confidence REAL, trend TEXT, priority_score REAL,
                episode_count INTEGER, attempt_count INTEGER, independent_pass_count INTEGER,
                error_episode_count INTEGER, recent_error_types_json TEXT, first_practiced_at TEXT,
                last_practiced_at TEXT, next_review_at TEXT, summary TEXT, content_hash TEXT,
                structured_payload TEXT, create_time TEXT, update_time TEXT)"""
        )
        connection.exec_driver_sql(
            """CREATE TABLE tb_ai_learning_state_evidence (
                state_id TEXT, memory_id TEXT, observed_at TEXT, contribution REAL,
                reason TEXT, structured_payload TEXT, create_time TEXT,
                PRIMARY KEY(state_id, memory_id))"""
        )
        connection.exec_driver_sql(
            """CREATE TABLE tb_ai_learning_state_projection (
                user_id INTEGER PRIMARY KEY, source_fingerprint TEXT, state_count INTEGER,
                last_sync_at TEXT, create_time TEXT, update_time TEXT)"""
        )
        for question_id in range(101, 106):
            connection.exec_driver_sql(
                "INSERT INTO tb_question VALUES (?, ?, 2, 'binary search', 'array,binary search', NULL)",
                (question_id, f"Binary Problem {question_id}"),
            )
        now = datetime.now(timezone.utc).replace(microsecond=0)
        submissions = [
            (1, 7, 101, None, 0, "secret-code-1", 0, 0, "Wrong Answer", 10, 100, 1, None, now - timedelta(days=12)),
            (2, 7, 101, None, 0, "secret-code-2", 1, 100, "Accepted", 8, 90, 1, None, now - timedelta(days=12, hours=-1)),
            (3, 7, 102, None, 0, "secret-code-3", 0, 0, "Wrong Answer", 11, 110, 1, None, now - timedelta(days=9)),
            (4, 7, 102, None, 0, "secret-code-4", 1, 100, "Accepted", 7, 85, 1, None, now - timedelta(days=9, hours=-1)),
            (5, 7, 103, None, 0, "secret-code-5", 1, 100, "Accepted", 6, 80, 1, None, now - timedelta(days=5)),
            (6, 7, 104, 201, 0, "secret-code-6", 1, 80, "Accepted", 9, 95, 1, None, now - timedelta(days=2)),
            (7, 8, 105, None, 0, "other-user-code", 0, 0, "Runtime Error", 2, 70, 1, None, now - timedelta(days=1)),
        ]
        for row in submissions:
            occurred = row[-1].isoformat()
            connection.exec_driver_sql(
                "INSERT INTO tb_user_submit VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (*row[:-1], occurred, occurred, occurred),
            )
        connection.exec_driver_sql(
            "INSERT INTO tb_exam VALUES (201, 'Binary Midterm', ?, NULL)",
            ((now - timedelta(days=2)).isoformat(),),
        )
        connection.exec_driver_sql(
            "INSERT INTO tb_user_exam VALUES (301, 7, 201, 80, 3, ?, ?)",
            ((now - timedelta(days=2)).isoformat(), (now - timedelta(days=2)).isoformat()),
        )
    engine.dispose()
    return database_url


def test_three_level_projection_and_recall_are_evidence_backed(tmp_path):
    repository = LearningMemoryRepository(_database(tmp_path))
    service = LearningMemoryService(repository, index=DisabledMemoryIndex())
    try:
        sync = service.sync_user(user_id="7")
        assert sync["source_submissions"] == 6
        assert sync["source_exams"] == 1
        assert sync["events"] == 7
        assert sync["episodes"] == 5
        assert sync["patterns"] >= 1

        recalled = service.recall(
            user_id="7",
            query="过去是否反复出现二分答案错误",
            knowledge_tags=["binary search"],
        )
        assert recalled["retrieval_mode"] == "database"
        assert recalled["patterns"]
        assert recalled["episodes"]
        assert recalled["events"]
        assert service.sync_user(user_id="7")["unchanged"] is True
        pattern = recalled["patterns"][0]
        assert pattern["memory_level"] == "pattern"
        assert pattern["occurrence_count"] == 2
        assert pattern["memory_status"] == "improving"

        detail = service.detail(user_id="7", memory_id=pattern["memory_id"])
        assert len(detail["evidence"]) == 2
        assert all(item["evidence_type"] == "episode" for item in detail["evidence"])

        exam_memory = next(
            item
            for item in repository.memories(user_id="7", levels=("event",), time_range_days=36500)
            if item["memory_type"] == "exam_result"
        )
        exam_detail = service.detail(user_id="7", memory_id=exam_memory["memory_id"])
        assert any(
            item["evidence_type"] == "exam" and item["evidence_id"] == "301"
            for item in exam_detail["evidence"]
        )

        occurred = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with repository.engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO tb_user_submit VALUES "
                "(8, 7, 105, NULL, 0, 'new-secret-code', 1, 100, 'Accepted', 5, 75, 1, NULL, ?, ?, ?)",
                (occurred, occurred, occurred),
            )
        refreshed = service.sync_user(user_id="7")
        assert refreshed["unchanged"] is False
        assert refreshed["events"] == 8

        with repository.engine.connect() as connection:
            serialized = " ".join(
                str(value)
                for row in connection.exec_driver_sql(
                    "SELECT summary, structured_payload FROM tb_ai_learning_memory WHERE user_id = 7"
                ).all()
                for value in row
            )
        assert "secret-code" not in serialized
    finally:
        repository.close()


def test_learning_memory_is_strictly_user_scoped(tmp_path):
    repository = LearningMemoryRepository(_database(tmp_path))
    service = LearningMemoryService(repository, index=DisabledMemoryIndex())
    try:
        service.sync_user(user_id="7")
        service.sync_user(user_id="8")
        user_seven = service.recall(user_id="7", query="运行错误", levels=["event"])
        user_eight = service.recall(user_id="8", query="运行错误", levels=["event"])
        assert all("Runtime Error" not in item["summary"] for item in user_seven["events"])
        assert any("runtime_error" in item["summary"] for item in user_eight["events"])

        foreign_id = user_eight["events"][0]["memory_id"]
        with pytest.raises(ValueError, match="not found"):
            service.detail(user_id="7", memory_id=foreign_id)
    finally:
        repository.close()


def test_learning_state_memory_is_dynamic_explainable_and_user_scoped(tmp_path):
    repository = LearningMemoryRepository(_database(tmp_path))
    memory_service = LearningMemoryService(repository, index=DisabledMemoryIndex())
    state_service = LearningStateService(repository, memory_service)
    try:
        recalled = state_service.recall(
            user_id="7",
            knowledge_tags=["Binary Search"],
            focus="all",
        )
        assert recalled["memory_domain"] == "learning_state"
        assert recalled["projection"] == {"states": 2, "unchanged": False}
        assert len(recalled["states"]) == 1
        state = recalled["states"][0]
        assert state["knowledge_tag"] == "binary search"
        assert state["episode_count"] == 4
        assert state["attempt_count"] == 6
        assert state["independent_pass_count"] == 4
        assert state["mastery_level"] == "stable"
        assert 0 < state["confidence"] < 1

        detail = state_service.detail(user_id="7", state_id=state["state_id"])
        assert len(detail["evidence"]) == 4
        assert all(item["memory_id"] for item in detail["evidence"])
        assert state_service.sync_user(user_id="7")["unchanged"] is True

        occurred = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with repository.engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE tb_question SET difficulty = 3, update_time = ? WHERE question_id = 104",
                (occurred,),
            )
        metadata_refresh = state_service.recall(
            user_id="7",
            knowledge_tags=["binary search"],
            focus="all",
        )
        assert metadata_refresh["projection"]["unchanged"] is False

        with repository.engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO tb_user_submit VALUES "
                "(8, 7, 105, NULL, 0, 'state-secret-code', 0, 0, 'Wrong Answer', 5, 75, 1, NULL, ?, ?, ?)",
                (occurred, occurred, occurred),
            )
        refreshed = state_service.recall(user_id="7", knowledge_tags=["binary search"], focus="all")
        assert refreshed["projection"]["unchanged"] is False
        assert refreshed["states"][0]["episode_count"] == 5
        assert refreshed["states"][0]["mastery_score"] < state["mastery_score"]

        state_service.sync_user(user_id="8")
        other = state_service.recall(user_id="8", focus="all")["states"][0]
        assert other["mastery_level"] == "insufficient"
        with pytest.raises(ValueError, match="not found"):
            state_service.detail(user_id="7", state_id=other["state_id"])

        with repository.engine.connect() as connection:
            serialized = " ".join(
                str(value)
                for row in connection.exec_driver_sql(
                    "SELECT summary, structured_payload FROM tb_ai_learning_state_memory WHERE user_id = 7"
                ).all()
                for value in row
            )
        assert "state-secret-code" not in serialized
    finally:
        repository.close()


def test_pending_submissions_and_unscored_exams_are_not_projected(tmp_path):
    repository = LearningMemoryRepository(_database(tmp_path))
    service = LearningMemoryService(repository, index=DisabledMemoryIndex())
    try:
        occurred = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with repository.engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO tb_user_submit VALUES "
                "(8, 7, 105, NULL, 0, 'pending-secret-code', 0, 0, 'Pending', 0, 0, 0, NULL, ?, ?, ?)",
                (occurred, occurred, occurred),
            )
            connection.exec_driver_sql(
                "INSERT INTO tb_exam VALUES (202, 'Pending Exam', ?, NULL)",
                (occurred,),
            )
            connection.exec_driver_sql(
                "INSERT INTO tb_user_exam VALUES (302, 7, 202, NULL, NULL, ?, ?)",
                (occurred, occurred),
            )

        sync = service.sync_user(user_id="7")
        assert sync["source_submissions"] == 6
        assert sync["source_exams"] == 1
        assert sync["events"] == 7
        assert sync["episodes"] == 5

        with repository.engine.connect() as connection:
            serialized = " ".join(
                str(value)
                for row in connection.exec_driver_sql(
                    "SELECT title, summary, structured_payload FROM tb_ai_learning_memory WHERE user_id = 7"
                ).all()
                for value in row
            )
        assert "Pending Exam" not in serialized
        assert "pending-secret-code" not in serialized
    finally:
        repository.close()


def test_problem_episode_uses_the_last_submission_as_its_final_result():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    common = {
        "question_id": 101,
        "exam_id": None,
        "program_type": 0,
        "score": 0,
        "use_time": 1,
        "use_memory": 1,
        "judge_status": 1,
        "last_error": None,
        "title": "Binary Search",
        "algorithm_tag": "binary search",
        "knowledge_tags": "array,binary search",
    }
    memories = project_learning_memories(
        user_id="7",
        submissions=[
            {**common, "submit_id": 1, "pass": 1, "exe_message": "Accepted", "occurred_at": now},
            {
                **common,
                "submit_id": 2,
                "pass": 0,
                "exe_message": "Wrong Answer",
                "occurred_at": now + timedelta(minutes=5),
            },
        ],
        exams=[],
        now=now + timedelta(minutes=5),
    )

    episode = next(item for item in memories if item.memory_type == "problem_episode")
    assert episode.payload["result_path"] == ["AC", "wrong_answer"]
    assert episode.payload["final_result"] == "failed"
    assert "最终未通过" in episode.summary


def test_learning_state_tracks_trend_and_time_based_review_priority():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    episodes = []
    for index in range(6):
        passed = index >= 3
        occurred = now - timedelta(days=60 - index * 10)
        episodes.append({
            "memory_id": f"{index:064x}",
            "memory_type": "problem_episode",
            "source_id": f"{100 + index}:practice:{index}",
            "knowledge_tags": ["Graph"],
            "first_seen_at": occurred,
            "last_seen_at": occurred,
            "payload": {
                "question_id": str(100 + index),
                "difficulty": 2,
                "attempt_count": 1,
                "final_result": "passed" if passed else "failed",
                "error_types": [] if passed else ["wrong_answer"],
            },
        })

    current = project_learning_states(user_id="7", episodes=episodes, now=now)[0]
    later = project_learning_states(user_id="7", episodes=episodes, now=now + timedelta(days=90))[0]
    assert current.knowledge_tag == "graph"
    assert current.trend == "improving"
    assert current.confidence > 0.7
    assert later.priority_score > current.priority_score


def test_learning_memory_validates_requested_levels(tmp_path):
    repository = LearningMemoryRepository(_database(tmp_path))
    service = LearningMemoryService(repository, index=DisabledMemoryIndex())
    try:
        with pytest.raises(ValueError, match="Unsupported"):
            service.recall(user_id="7", query="history", levels=["conversation"])
    finally:
        repository.close()
