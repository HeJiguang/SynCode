from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, RowMapping


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _row(row: RowMapping | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: _json_value(value) for key, value in row.items()}


class LearningRepository:
    """Small, read-only query surface for tools owned by the current user."""

    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)

    def close(self) -> None:
        self.engine.dispose()

    def get_question(self, question_id: str) -> dict[str, Any] | None:
        self._question_id(question_id)
        statement = text(
            """
            SELECT question_id, title, difficulty, algorithm_tag, knowledge_tags,
                   estimated_minutes, time_limit, space_limit, content, default_code
            FROM tb_question
            WHERE question_id = :question_id
            LIMIT 1
            """
        )
        with self.engine.connect() as connection:
            return _row(connection.execute(statement, {"question_id": question_id}).mappings().first())

    def get_submission_history(self, user_id: str, question_id: str, limit: int = 5) -> list[dict[str, Any]]:
        self._user_id(user_id)
        self._question_id(question_id)
        safe_limit = max(1, min(int(limit), 10))
        statement = text(
            """
            SELECT submit_id, question_id, program_type, user_code, pass, score,
                   exe_message, case_judge_res, use_time, use_memory,
                   judge_status, create_time, update_time
            FROM tb_user_submit
            WHERE user_id = :user_id AND question_id = :question_id
            ORDER BY COALESCE(update_time, create_time) DESC, submit_id DESC
            LIMIT :limit
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement,
                {"user_id": user_id, "question_id": question_id, "limit": safe_limit},
            ).mappings().all()
        return [_row(row) or {} for row in rows]

    def get_learning_profile(self, user_id: str) -> dict[str, Any]:
        self._user_id(user_id)
        counts_sql = text(
            """
            SELECT COUNT(*) AS submission_count,
                   COUNT(DISTINCT CASE WHEN pass = 1 THEN question_id END) AS solved_count
            FROM tb_user_submit
            WHERE user_id = :user_id
            """
        )
        profile_sql = text(
            """
            SELECT current_level, target_direction, weak_points, strong_points,
                   last_test_exam_id, last_plan_id
            FROM tb_training_profile
            WHERE user_id = :user_id AND status = 1
            LIMIT 1
            """
        )
        with self.engine.connect() as connection:
            counts = _row(connection.execute(counts_sql, {"user_id": user_id}).mappings().first()) or {}
            profile = _row(connection.execute(profile_sql, {"user_id": user_id}).mappings().first())
        return {**counts, "training_profile": profile}

    def get_current_training_plan(self, user_id: str) -> dict[str, Any] | None:
        self._user_id(user_id)
        plan_sql = text(
            """
            SELECT plan_id, plan_title, plan_goal, source_type, based_on_exam_id,
                   plan_status, ai_summary, create_time, update_time
            FROM tb_training_plan
            WHERE user_id = :user_id AND plan_status IN (0, 1)
            ORDER BY CASE WHEN plan_status = 1 THEN 0 ELSE 1 END, create_time DESC
            LIMIT 1
            """
        )
        task_sql = text(
            """
            SELECT task_id, task_type, question_id, exam_id, title_snapshot,
                   task_order, task_status, recommended_reason,
                   knowledge_tags_snapshot, due_time
            FROM tb_training_task
            WHERE user_id = :user_id AND plan_id = :plan_id
            ORDER BY task_order ASC, task_id ASC
            """
        )
        with self.engine.connect() as connection:
            plan = _row(connection.execute(plan_sql, {"user_id": user_id}).mappings().first())
            if plan is None:
                return None
            tasks = connection.execute(
                task_sql,
                {"user_id": user_id, "plan_id": plan["plan_id"]},
            ).mappings().all()
        return {**plan, "tasks": [_row(row) or {} for row in tasks]}

    def search_practice_questions(
        self,
        user_id: str,
        *,
        knowledge_tag: str | None = None,
        difficulty: int | None = None,
        exclude_solved: bool = True,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        self._user_id(user_id)
        safe_limit = max(1, min(int(limit), 20))
        clauses = ["COALESCE(q.training_enabled, 1) = 1"]
        params: dict[str, Any] = {"user_id": user_id, "limit": safe_limit}
        if knowledge_tag and knowledge_tag.strip():
            clauses.append("(q.knowledge_tags LIKE :tag OR q.algorithm_tag LIKE :tag)")
            params["tag"] = f"%{knowledge_tag.strip()[:80]}%"
        if difficulty is not None:
            safe_difficulty = int(difficulty)
            if safe_difficulty not in (1, 2, 3):
                raise ValueError("difficulty must be 1, 2, or 3")
            clauses.append("q.difficulty = :difficulty")
            params["difficulty"] = safe_difficulty
        if exclude_solved:
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM tb_user_submit s "
                "WHERE s.user_id = :user_id AND s.question_id = q.question_id AND s.pass = 1)"
            )
        statement = text(
            f"""
            SELECT q.question_id, q.title, q.difficulty, q.algorithm_tag,
                   q.knowledge_tags, q.estimated_minutes
            FROM tb_question q
            WHERE {' AND '.join(clauses)}
            ORDER BY q.difficulty ASC, q.question_id ASC
            LIMIT :limit
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement, params).mappings().all()
        return [_row(row) or {} for row in rows]

    @staticmethod
    def _user_id(value: str) -> None:
        if not value.isdecimal():
            raise ValueError("user identity is invalid")

    @staticmethod
    def _question_id(value: str) -> None:
        if not value.isdecimal():
            raise ValueError("question_id must contain digits only")
