from __future__ import annotations

from datetime import date, datetime
import json
from typing import Any
from uuid import uuid4

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
    """User-scoped learning data surface used by Hermes MCP tools."""

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

    def get_recent_submissions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        self._user_id(user_id)
        safe_limit = max(1, min(int(limit), 50))
        statement = text(
            """
            SELECT s.submit_id, s.question_id, q.title, q.difficulty,
                   q.algorithm_tag, q.knowledge_tags, s.program_type,
                   s.pass, s.score, s.exe_message, s.judge_status,
                   s.create_time, s.update_time
            FROM tb_user_submit s
            LEFT JOIN tb_question q ON q.question_id = s.question_id
            WHERE s.user_id = :user_id
            ORDER BY COALESCE(s.update_time, s.create_time) DESC, s.submit_id DESC
            LIMIT :limit
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement,
                {"user_id": user_id, "limit": safe_limit},
            ).mappings().all()
        return [_row(row) or {} for row in rows]

    def list_learning_profile_sources(self, limit: int = 500) -> list[dict[str, str]]:
        safe_limit = max(1, min(int(limit), 5000))
        statement = text(
            """
            SELECT user_id, MAX(submit_id) AS max_submit_id,
                   COUNT(*) AS submission_count,
                   MAX(COALESCE(update_time, create_time)) AS latest_activity
            FROM tb_user_submit
            WHERE user_id IS NOT NULL
            GROUP BY user_id
            ORDER BY latest_activity DESC, user_id ASC
            LIMIT :limit
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement, {"limit": safe_limit}).mappings().all()
        sources: list[dict[str, str]] = []
        for row in rows:
            latest = _json_value(row["latest_activity"])
            sources.append(
                {
                    "user_id": str(row["user_id"]),
                    "source_watermark": (
                        f"{row['max_submit_id']}:{row['submission_count']}:{latest or 'unknown'}"
                    ),
                }
            )
        return sources

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

    def save_training_plan(
        self,
        user_id: str,
        *,
        plan_title: str,
        plan_goal: str,
        tasks: list[dict[str, Any]],
        ai_summary: str | None = None,
    ) -> dict[str, Any]:
        self._user_id(user_id)
        title = self._bounded_text(plan_title, "plan_title", 100)
        goal = self._bounded_text(plan_goal, "plan_goal", 255)
        summary = self._optional_text(ai_summary, 2000)
        if not 1 <= len(tasks) <= 10:
            raise ValueError("tasks must contain between 1 and 10 items")
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, task in enumerate(tasks, start=1):
            if not isinstance(task, dict):
                raise ValueError("each task must be an object")
            question_id = str(task.get("question_id") or "").strip()
            self._question_id(question_id)
            if question_id in seen:
                raise ValueError("training plan contains a duplicate question")
            seen.add(question_id)
            normalized.append(
                {
                    "task_id": self._new_id(),
                    "question_id": question_id,
                    "task_order": index,
                    "recommended_reason": self._bounded_text(
                        str(task.get("recommended_reason") or "Practice this question."),
                        "recommended_reason",
                        500,
                    ),
                    "due_time": self._due_time(task.get("due_time")),
                }
            )

        question_sql = text(
            "SELECT question_id, title, knowledge_tags FROM tb_question "
            "WHERE question_id = :question_id AND COALESCE(training_enabled, 1) = 1 LIMIT 1"
        )
        with self.engine.begin() as connection:
            plan_id = self._new_id()
            questions: dict[str, dict[str, Any]] = {}
            for task in normalized:
                question = _row(
                    connection.execute(question_sql, {"question_id": task["question_id"]}).mappings().first()
                )
                if question is None:
                    raise ValueError(f"question {task['question_id']} is not available for training")
                questions[task["question_id"]] = question

            connection.execute(
                text(
                    "UPDATE tb_training_plan SET plan_status = 3, update_by = :user_id, "
                    "update_time = CURRENT_TIMESTAMP "
                    "WHERE user_id = :user_id AND plan_status IN (0, 1)"
                ),
                {"user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO tb_training_plan(plan_id, user_id, plan_title, plan_goal, source_type, "
                    "plan_status, ai_summary, create_by, create_time, update_by, update_time) "
                    "VALUES (:plan_id, :user_id, :title, :goal, 'hermes_agent', 1, :summary, :user_id, "
                    "CURRENT_TIMESTAMP, :user_id, CURRENT_TIMESTAMP)"
                ),
                {
                    "plan_id": plan_id,
                    "user_id": user_id,
                    "title": title,
                    "goal": goal,
                    "summary": summary,
                },
            )
            for task in normalized:
                question = questions[task["question_id"]]
                connection.execute(
                    text(
                        "INSERT INTO tb_training_task(task_id, plan_id, user_id, task_type, question_id, "
                        "title_snapshot, task_order, task_status, recommended_reason, knowledge_tags_snapshot, "
                        "due_time, create_by, create_time, update_by, update_time) VALUES (:task_id, :plan_id, "
                        ":user_id, 'question', :question_id, :title, :task_order, 0, :reason, :tags, :due_time, "
                        ":user_id, CURRENT_TIMESTAMP, :user_id, CURRENT_TIMESTAMP)"
                    ),
                    {
                        "task_id": task["task_id"],
                        "plan_id": plan_id,
                        "user_id": user_id,
                        "question_id": task["question_id"],
                        "title": question["title"],
                        "task_order": task["task_order"],
                        "reason": task["recommended_reason"],
                        "tags": question.get("knowledge_tags"),
                        "due_time": task["due_time"],
                    },
                )
                self._record_recommendation_event(
                    connection,
                    user_id=user_id,
                    recommendation_id=f"plan-{plan_id}-question-{task['question_id']}",
                    action="accepted",
                    question_id=task["question_id"],
                    plan_id=plan_id,
                    task_id=task["task_id"],
                    run_id=None,
                    metadata={"reason": task["recommended_reason"]},
                )
            updated = connection.execute(
                text(
                    "UPDATE tb_training_profile SET last_plan_id = :plan_id, update_by = :user_id, "
                    "update_time = CURRENT_TIMESTAMP "
                    "WHERE user_id = :user_id AND status = 1"
                ),
                {"plan_id": plan_id, "user_id": user_id},
            )
            if updated.rowcount == 0:
                connection.execute(
                    text(
                        "INSERT INTO tb_training_profile(profile_id, user_id, current_level, target_direction, "
                        "weak_points, strong_points, last_plan_id, status, create_by, create_time, update_by, "
                        "update_time) VALUES (:profile_id, :user_id, 'starter', 'algorithm_foundation', '', '', "
                        ":plan_id, 1, :user_id, CURRENT_TIMESTAMP, :user_id, CURRENT_TIMESTAMP)"
                    ),
                    {"profile_id": self._new_id(), "user_id": user_id, "plan_id": plan_id},
                )
        plan = self.get_current_training_plan(user_id)
        if plan is None:
            raise RuntimeError("saved training plan could not be reloaded")
        return plan

    def update_training_task(self, user_id: str, task_id: str, task_status: int = 1) -> dict[str, Any]:
        self._user_id(user_id)
        self._numeric_id(task_id, "task_id")
        if int(task_status) not in (0, 1, 2):
            raise ValueError("task_status must be 0, 1, or 2")
        with self.engine.begin() as connection:
            task = _row(
                connection.execute(
                    text(
                        "SELECT task_id, plan_id, question_id, task_status FROM tb_training_task "
                        "WHERE task_id = :task_id AND user_id = :user_id LIMIT 1"
                    ),
                    {"task_id": task_id, "user_id": user_id},
                ).mappings().first()
            )
            if task is None:
                raise KeyError(task_id)
            connection.execute(
                text(
                    "UPDATE tb_training_task SET task_status = :status, update_by = :user_id, "
                    "update_time = CURRENT_TIMESTAMP "
                    "WHERE task_id = :task_id AND user_id = :user_id"
                ),
                {"status": int(task_status), "task_id": task_id, "user_id": user_id},
            )
            pending = connection.execute(
                text(
                    "SELECT COUNT(*) FROM tb_training_task WHERE plan_id = :plan_id AND user_id = :user_id "
                    "AND task_status = 0"
                ),
                {"plan_id": task["plan_id"], "user_id": user_id},
            ).scalar_one()
            if int(pending) == 0:
                connection.execute(
                    text(
                        "UPDATE tb_training_plan SET plan_status = 2, update_by = :user_id, "
                        "update_time = CURRENT_TIMESTAMP "
                        "WHERE plan_id = :plan_id AND user_id = :user_id"
                    ),
                    {"plan_id": task["plan_id"], "user_id": user_id},
                )
            self._record_recommendation_event(
                connection,
                user_id=user_id,
                recommendation_id=f"plan-{task['plan_id']}-question-{task.get('question_id')}",
                action="completed" if int(task_status) == 1 else "skipped" if int(task_status) == 2 else "reopened",
                question_id=str(task.get("question_id")) if task.get("question_id") is not None else None,
                plan_id=int(task["plan_id"]),
                task_id=int(task["task_id"]),
                run_id=None,
                metadata={},
            )
        return {
            "task_id": int(task_id),
            "plan_id": task["plan_id"],
            "task_status": int(task_status),
            "plan_completed": int(pending) == 0,
        }

    def record_recommendation_feedback(
        self,
        user_id: str,
        *,
        recommendation_id: str,
        action: str,
        question_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        self._user_id(user_id)
        recommendation = self._bounded_text(recommendation_id, "recommendation_id", 128)
        normalized_action = action.strip().lower()
        if normalized_action not in {"impression", "opened", "accepted", "skipped"}:
            raise ValueError("unsupported recommendation action")
        if question_id is not None:
            self._question_id(question_id)
        with self.engine.begin() as connection:
            if question_id is not None:
                exists = connection.execute(
                    text("SELECT 1 FROM tb_question WHERE question_id = :question_id LIMIT 1"),
                    {"question_id": question_id},
                ).first()
                if exists is None:
                    raise ValueError(f"question {question_id} does not exist")
            event_id = self._record_recommendation_event(
                connection,
                user_id=user_id,
                recommendation_id=recommendation,
                action=normalized_action,
                question_id=question_id,
                plan_id=None,
                task_id=None,
                run_id=self._optional_text(run_id, 160),
                metadata={},
            )
        return {
            "event_id": event_id,
            "recommendation_id": recommendation,
            "action": normalized_action,
            "question_id": question_id,
        }

    def get_training_effects(self, user_id: str, plan_id: str | None = None) -> dict[str, Any]:
        self._user_id(user_id)
        if plan_id is not None:
            self._numeric_id(plan_id, "plan_id")
        with self.engine.connect() as connection:
            if plan_id is None:
                plan = _row(
                    connection.execute(
                        text(
                            "SELECT plan_id, plan_title, plan_status, create_time, update_time "
                            "FROM tb_training_plan WHERE user_id = :user_id ORDER BY plan_id DESC LIMIT 1"
                        ),
                        {"user_id": user_id},
                    ).mappings().first()
                )
            else:
                plan = _row(
                    connection.execute(
                        text(
                            "SELECT plan_id, plan_title, plan_status, create_time, update_time "
                            "FROM tb_training_plan WHERE user_id = :user_id AND plan_id = :plan_id LIMIT 1"
                        ),
                        {"user_id": user_id, "plan_id": plan_id},
                    ).mappings().first()
                )
            if plan is None:
                return {"plan": None, "summary": {"task_count": 0, "completed_tasks": 0, "passed_questions": 0}, "tasks": []}
            rows = connection.execute(
                text(
                    "SELECT task_id, question_id, title_snapshot, task_order, task_status "
                    "FROM tb_training_task WHERE user_id = :user_id AND plan_id = :plan_id ORDER BY task_order"
                ),
                {"user_id": user_id, "plan_id": plan["plan_id"]},
            ).mappings().all()
            tasks: list[dict[str, Any]] = []
            for raw in rows:
                task = _row(raw) or {}
                if task.get("question_id") is not None:
                    effect = _row(
                        connection.execute(
                            text(
                                "SELECT COUNT(*) AS attempts, MAX(CASE WHEN pass = 1 THEN 1 ELSE 0 END) AS passed, "
                                "MAX(score) AS best_score, MAX(COALESCE(update_time, create_time)) AS latest_submit_time "
                                "FROM tb_user_submit WHERE user_id = :user_id AND question_id = :question_id "
                                "AND COALESCE(update_time, create_time) >= :plan_created_at"
                            ),
                            {
                                "user_id": user_id,
                                "question_id": task["question_id"],
                                "plan_created_at": plan["create_time"],
                            },
                        ).mappings().first()
                    ) or {}
                    task["effect"] = effect
                tasks.append(task)
        return {
            "plan": plan,
            "summary": {
                "task_count": len(tasks),
                "completed_tasks": sum(1 for task in tasks if int(task.get("task_status") or 0) == 1),
                "skipped_tasks": sum(1 for task in tasks if int(task.get("task_status") or 0) == 2),
                "passed_questions": sum(1 for task in tasks if int((task.get("effect") or {}).get("passed") or 0) == 1),
                "attempts": sum(int((task.get("effect") or {}).get("attempts") or 0) for task in tasks),
            },
            "tasks": tasks,
        }

    @staticmethod
    def _record_recommendation_event(
        connection: Any,
        *,
        user_id: str,
        recommendation_id: str,
        action: str,
        question_id: str | None,
        plan_id: int | None,
        task_id: int | None,
        run_id: str | None,
        metadata: dict[str, Any],
    ) -> int:
        result = connection.execute(
            text(
                "INSERT INTO tb_ai_recommendation_event(user_id, recommendation_id, action, question_id, "
                "plan_id, task_id, run_id, metadata_json, create_time) VALUES (:user_id, :recommendation_id, "
                ":action, :question_id, :plan_id, :task_id, :run_id, :metadata, CURRENT_TIMESTAMP)"
            ),
            {
                "user_id": user_id,
                "recommendation_id": recommendation_id,
                "action": action,
                "question_id": question_id,
                "plan_id": plan_id,
                "task_id": task_id,
                "run_id": run_id,
                "metadata": json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
            },
        )
        return int(result.lastrowid)

    @staticmethod
    def _new_id() -> int:
        return (uuid4().int & ((1 << 63) - 1)) or 1

    @staticmethod
    def _bounded_text(value: str, field: str, limit: int) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        if len(normalized) > limit:
            raise ValueError(f"{field} exceeds {limit} characters")
        return normalized

    @staticmethod
    def _optional_text(value: Any, limit: int) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        if len(normalized) > limit:
            raise ValueError(f"text exceeds {limit} characters")
        return normalized

    @staticmethod
    def _numeric_id(value: str, field: str) -> None:
        if not str(value).isdecimal():
            raise ValueError(f"{field} must contain digits only")

    @staticmethod
    def _due_time(value: Any) -> str | None:
        if value in (None, ""):
            return None
        normalized = str(value).strip()
        try:
            datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("due_time must be an ISO-8601 timestamp") from exc
        return normalized

    @staticmethod
    def _user_id(value: str) -> None:
        if not value.isdecimal():
            raise ValueError("user identity is invalid")

    @staticmethod
    def _question_id(value: str) -> None:
        if not value.isdecimal():
            raise ValueError("question_id must contain digits only")
