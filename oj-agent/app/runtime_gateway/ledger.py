from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterator
from uuid import uuid4


TERMINAL_RUN_STATUSES = {"completed", "failed", "cancelled", "interrupted"}


class AdmissionLimitExceeded(RuntimeError):
    def __init__(self, scope: str, limit: int) -> None:
        super().__init__(f"Too many concurrent Agent runs for {scope} (limit {limit}).")
        self.scope = scope
        self.limit = limit


class LedgerOwnershipError(RuntimeError):
    pass


class ProfileRefreshBusy(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AdmissionReservation:
    reservation_id: str
    user_id: str
    runtime_name: str


@dataclass(frozen=True, slots=True)
class ProfileRefreshReservation:
    user_id: str
    source_watermark: str
    previous_watermark: str | None


class RuntimeLedger:
    """Durable, user-scoped projection of Runtime runs, SSE events and artifacts."""

    def __init__(
        self,
        path: Path,
        *,
        per_user_limit: int,
        per_runtime_limit: int,
        stale_after_seconds: int,
    ) -> None:
        self.path = path
        self.per_user_limit = max(0, int(per_user_limit))
        self.per_runtime_limit = max(0, int(per_runtime_limit))
        self.stale_after_seconds = max(60, int(stale_after_seconds))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runtime_runs (
                    public_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    runtime_name TEXT NOT NULL,
                    native_id TEXT NOT NULL,
                    session_public_id TEXT,
                    workflow TEXT,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    completed_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_runtime_runs_user_active
                    ON runtime_runs(user_id, status, updated_at);
                CREATE INDEX IF NOT EXISTS idx_runtime_runs_runtime_active
                    ON runtime_runs(runtime_name, status, updated_at);

                CREATE TABLE IF NOT EXISTS runtime_admissions (
                    reservation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    runtime_name TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_runtime_admissions_user
                    ON runtime_admissions(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_runtime_admissions_runtime
                    ON runtime_admissions(runtime_name, created_at);

                CREATE TABLE IF NOT EXISTS runtime_events (
                    run_public_id TEXT NOT NULL,
                    sequence_no INTEGER NOT NULL,
                    upstream_event_id TEXT,
                    event_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    frame TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (run_public_id, sequence_no)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_events_upstream_id
                    ON runtime_events(run_public_id, upstream_event_id)
                    WHERE upstream_event_id IS NOT NULL;

                CREATE TABLE IF NOT EXISTS runtime_artifacts (
                    public_id TEXT PRIMARY KEY,
                    run_public_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    body_json TEXT NOT NULL,
                    render_hint TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_runtime_artifacts_run
                    ON runtime_artifacts(run_public_id, created_at);

                CREATE TABLE IF NOT EXISTS learning_profile_refreshes (
                    user_id TEXT PRIMARY KEY,
                    source_watermark TEXT NOT NULL,
                    state TEXT NOT NULL,
                    run_public_id TEXT,
                    runtime_name TEXT,
                    updated_at REAL NOT NULL
                );
                """
            )

    def close(self) -> None:
        return

    def reserve(self, user_id: str, runtime_name: str) -> AdmissionReservation:
        now = time.time()
        cutoff = now - self.stale_after_seconds
        reservation = AdmissionReservation(f"adm_{uuid4().hex}", user_id, runtime_name)
        with self._transaction() as connection:
            connection.execute("DELETE FROM runtime_admissions WHERE created_at < ?", (cutoff,))
            connection.execute(
                "UPDATE runtime_runs SET status = 'interrupted', updated_at = ?, completed_at = ? "
                "WHERE status NOT IN ('completed', 'failed', 'cancelled', 'interrupted') AND updated_at < ?",
                (now, now, cutoff),
            )
            user_active = self._active_count(connection, "user_id", user_id)
            user_pending = self._reservation_count(connection, "user_id", user_id)
            if self.per_user_limit and user_active + user_pending >= self.per_user_limit:
                raise AdmissionLimitExceeded("this user", self.per_user_limit)
            runtime_active = self._active_count(connection, "runtime_name", runtime_name)
            runtime_pending = self._reservation_count(connection, "runtime_name", runtime_name)
            if self.per_runtime_limit and runtime_active + runtime_pending >= self.per_runtime_limit:
                raise AdmissionLimitExceeded(f"Runtime {runtime_name}", self.per_runtime_limit)
            connection.execute(
                "INSERT INTO runtime_admissions(reservation_id, user_id, runtime_name, created_at) VALUES (?, ?, ?, ?)",
                (reservation.reservation_id, user_id, runtime_name, now),
            )
        return reservation

    def release(self, reservation: AdmissionReservation) -> None:
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM runtime_admissions WHERE reservation_id = ?",
                (reservation.reservation_id,),
            )

    def reserve_profile_refresh(
        self,
        user_id: str,
        source_watermark: str,
    ) -> ProfileRefreshReservation | None:
        """Atomically claim a changed learning-data snapshot for one user."""
        now = time.time()
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT p.source_watermark, p.state, p.run_public_id, r.status AS run_status "
                "FROM learning_profile_refreshes p "
                "LEFT JOIN runtime_runs r ON r.public_id = p.run_public_id "
                "WHERE p.user_id = ?",
                (user_id,),
            ).fetchone()
            if row is not None and row["source_watermark"] == source_watermark:
                return None
            if row is not None and row["state"] == "reserved":
                raise ProfileRefreshBusy("A learning profile refresh is already being reserved.")
            if (
                row is not None
                and row["state"] == "scheduled"
                and row["run_public_id"]
                and row["run_status"] not in TERMINAL_RUN_STATUSES
            ):
                raise ProfileRefreshBusy("A learning profile refresh is still running.")
            previous = str(row["source_watermark"]) if row is not None else None
            connection.execute(
                """
                INSERT INTO learning_profile_refreshes(
                    user_id, source_watermark, state, run_public_id, runtime_name, updated_at
                ) VALUES (?, ?, 'reserved', NULL, NULL, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    source_watermark = excluded.source_watermark,
                    state = 'reserved',
                    run_public_id = NULL,
                    runtime_name = NULL,
                    updated_at = excluded.updated_at
                """,
                (user_id, source_watermark, now),
            )
        return ProfileRefreshReservation(user_id, source_watermark, previous)

    def commit_profile_refresh(
        self,
        reservation: ProfileRefreshReservation,
        *,
        run_public_id: str,
        runtime_name: str,
    ) -> None:
        with self._transaction() as connection:
            updated = connection.execute(
                "UPDATE learning_profile_refreshes SET state = 'scheduled', run_public_id = ?, "
                "runtime_name = ?, updated_at = ? WHERE user_id = ? AND source_watermark = ? "
                "AND state = 'reserved'",
                (
                    run_public_id,
                    runtime_name,
                    time.time(),
                    reservation.user_id,
                    reservation.source_watermark,
                ),
            )
            if updated.rowcount != 1:
                raise LedgerOwnershipError("Learning profile refresh reservation is no longer valid.")

    def release_profile_refresh(self, reservation: ProfileRefreshReservation) -> None:
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT state, source_watermark FROM learning_profile_refreshes WHERE user_id = ?",
                (reservation.user_id,),
            ).fetchone()
            if (
                row is None
                or row["state"] != "reserved"
                or row["source_watermark"] != reservation.source_watermark
            ):
                return
            if reservation.previous_watermark is None:
                connection.execute(
                    "DELETE FROM learning_profile_refreshes WHERE user_id = ?",
                    (reservation.user_id,),
                )
            else:
                connection.execute(
                    "UPDATE learning_profile_refreshes SET source_watermark = ?, state = 'scheduled', "
                    "run_public_id = NULL, runtime_name = NULL, updated_at = ? WHERE user_id = ?",
                    (reservation.previous_watermark, time.time(), reservation.user_id),
                )

    def get_profile_refresh(self, user_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM learning_profile_refreshes WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def commit_run(
        self,
        reservation: AdmissionReservation,
        *,
        public_id: str,
        native_id: str,
        session_public_id: str | None,
        workflow: str | None,
        status: str,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
    ) -> None:
        now = time.time()
        normalized_status = _normalize_status(status)
        completed_at = now if normalized_status in TERMINAL_RUN_STATUSES else None
        with self._transaction() as connection:
            owned = connection.execute(
                "SELECT user_id, runtime_name FROM runtime_admissions WHERE reservation_id = ?",
                (reservation.reservation_id,),
            ).fetchone()
            if owned is None or owned["user_id"] != reservation.user_id or owned["runtime_name"] != reservation.runtime_name:
                raise LedgerOwnershipError("Run admission reservation is no longer valid.")
            connection.execute(
                """
                INSERT INTO runtime_runs(
                    public_id, user_id, runtime_name, native_id, session_public_id, workflow,
                    status, request_json, response_json, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(public_id) DO UPDATE SET
                    status = excluded.status,
                    response_json = excluded.response_json,
                    updated_at = excluded.updated_at,
                    completed_at = excluded.completed_at
                """,
                (
                    public_id,
                    reservation.user_id,
                    reservation.runtime_name,
                    native_id,
                    session_public_id,
                    workflow,
                    normalized_status,
                    _json(request_payload),
                    _json(response_payload),
                    now,
                    now,
                    completed_at,
                ),
            )
            connection.execute(
                "DELETE FROM runtime_admissions WHERE reservation_id = ?",
                (reservation.reservation_id,),
            )

    def get_run(self, public_id: str, user_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM runtime_runs WHERE public_id = ?",
                (public_id,),
            ).fetchone()
        if row is None:
            return None
        if row["user_id"] != user_id:
            raise LedgerOwnershipError("Run does not belong to the current user.")
        response = _object(row["response_json"])
        response.update(
            {
                "object": response.get("object", "syncode.run"),
                "run_id": public_id,
                "session_id": row["session_public_id"],
                "runtime": row["runtime_name"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "completed_at": row["completed_at"],
                "durable": True,
            }
        )
        return response

    def update_run(self, public_id: str, user_id: str, payload: dict[str, Any]) -> None:
        now = time.time()
        status = _normalize_status(str(payload.get("status") or "running"))
        completed_at = now if status in TERMINAL_RUN_STATUSES else None
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT user_id, response_json FROM runtime_runs WHERE public_id = ?",
                (public_id,),
            ).fetchone()
            if row is None:
                return
            if row["user_id"] != user_id:
                raise LedgerOwnershipError("Run does not belong to the current user.")
            merged = _object(row["response_json"])
            merged.update(payload)
            connection.execute(
                "UPDATE runtime_runs SET status = ?, response_json = ?, updated_at = ?, "
                "completed_at = COALESCE(completed_at, ?) WHERE public_id = ?",
                (status, _json(merged), now, completed_at, public_id),
            )

    def append_event(
        self,
        public_id: str,
        user_id: str,
        *,
        upstream_event_id: str | None,
        event_name: str,
        payload: dict[str, Any],
        frame: str,
    ) -> int | None:
        now = time.time()
        with self._transaction() as connection:
            self._assert_owned(connection, public_id, user_id)
            if upstream_event_id is not None:
                duplicate = connection.execute(
                    "SELECT sequence_no FROM runtime_events WHERE run_public_id = ? AND upstream_event_id = ?",
                    (public_id, upstream_event_id),
                ).fetchone()
                if duplicate is not None:
                    return None
            last = connection.execute(
                "SELECT MAX(sequence_no) AS value FROM runtime_events WHERE run_public_id = ?",
                (public_id,),
            ).fetchone()
            sequence = int(last["value"] if last and last["value"] is not None else -1) + 1
            if upstream_event_id is not None and upstream_event_id.isdigit():
                sequence = max(sequence, int(upstream_event_id))
            connection.execute(
                "INSERT INTO runtime_events(run_public_id, sequence_no, upstream_event_id, event_name, "
                "payload_json, frame, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (public_id, sequence, upstream_event_id, event_name, _json(payload), frame, now),
            )
            normalized = _status_from_event(event_name, payload)
            if normalized:
                run = connection.execute(
                    "SELECT response_json FROM runtime_runs WHERE public_id = ?",
                    (public_id,),
                ).fetchone()
                merged = _object(run["response_json"]) if run is not None else {}
                merged.update(payload)
                connection.execute(
                    "UPDATE runtime_runs SET status = ?, response_json = ?, updated_at = ?, "
                    "completed_at = CASE WHEN ? IS NULL THEN completed_at ELSE ? END WHERE public_id = ?",
                    (
                        normalized,
                        _json(merged),
                        now,
                        now if normalized in TERMINAL_RUN_STATUSES else None,
                        now if normalized in TERMINAL_RUN_STATUSES else None,
                        public_id,
                    ),
                )
            else:
                connection.execute(
                    "UPDATE runtime_runs SET updated_at = ? WHERE public_id = ?",
                    (now, public_id),
                )
            self._project_artifact(connection, public_id, user_id, event_name, payload, now)
            return sequence

    def list_events(self, public_id: str, user_id: str, *, after: int = -1) -> list[dict[str, Any]]:
        with self._connection() as connection:
            self._assert_owned(connection, public_id, user_id)
            rows = connection.execute(
                "SELECT sequence_no, upstream_event_id, event_name, payload_json, frame, created_at "
                "FROM runtime_events WHERE run_public_id = ? AND sequence_no > ? ORDER BY sequence_no ASC",
                (public_id, after),
            ).fetchall()
        return [
            {
                "sequence_no": row["sequence_no"],
                "upstream_event_id": row["upstream_event_id"],
                "event": row["event_name"],
                "payload": _object(row["payload_json"]),
                "frame": row["frame"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list_artifacts(self, public_id: str, user_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            self._assert_owned(connection, public_id, user_id)
            rows = connection.execute(
                "SELECT * FROM runtime_artifacts WHERE run_public_id = ? ORDER BY created_at ASC",
                (public_id,),
            ).fetchall()
        return [
            {
                "id": row["public_id"],
                "run_id": row["run_public_id"],
                "artifact_type": row["artifact_type"],
                "title": row["title"],
                "summary": row["summary"],
                "body": _object(row["body_json"]),
                "render_hint": row["render_hint"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def is_terminal(self, public_id: str, user_id: str) -> bool:
        run = self.get_run(public_id, user_id)
        return bool(run and run.get("status") in TERMINAL_RUN_STATUSES)

    def has_terminal_event(self, public_id: str, user_id: str) -> bool:
        with self._connection() as connection:
            self._assert_owned(connection, public_id, user_id)
            row = connection.execute(
                "SELECT 1 FROM runtime_events WHERE run_public_id = ? "
                "AND event_name IN ('run.completed', 'run.failed', 'run.cancelled', 'run.interrupted') LIMIT 1",
                (public_id,),
            ).fetchone()
        return row is not None

    def _project_artifact(
        self,
        connection: sqlite3.Connection,
        public_id: str,
        user_id: str,
        event_name: str,
        payload: dict[str, Any],
        created_at: float,
    ) -> None:
        artifact = payload.get("artifact") if event_name == "artifact.created" else None
        if isinstance(artifact, dict):
            body = artifact.get("body") if isinstance(artifact.get("body"), dict) else dict(artifact)
            artifact_type = str(artifact.get("artifact_type") or artifact.get("type") or "runtime_artifact")
            title = str(artifact.get("title") or "Agent artifact")[:255]
            summary = str(artifact.get("summary") or "")[:1000] or None
            render_hint = str(artifact.get("render_hint") or "markdown")
            source_key = str(artifact.get("id") or _json(artifact))
        elif event_name == "run.completed":
            output = payload.get("output")
            if not isinstance(output, str) or not output.strip():
                return
            workflow_row = connection.execute(
                "SELECT workflow FROM runtime_runs WHERE public_id = ?",
                (public_id,),
            ).fetchone()
            workflow = str(workflow_row["workflow"] or "") if workflow_row else ""
            artifact_type, title, render_hint = _workflow_artifact(workflow)
            body = {"output": output}
            summary = output.strip()[:1000]
            source_key = f"terminal:{public_id}"
        else:
            return
        digest = hashlib.sha256(f"{public_id}\0{source_key}".encode("utf-8")).hexdigest()[:24]
        connection.execute(
            """
            INSERT OR IGNORE INTO runtime_artifacts(
                public_id, run_public_id, user_id, artifact_type, title, summary,
                body_json, render_hint, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"art_{digest}",
                public_id,
                user_id,
                artifact_type,
                title,
                summary,
                _json(body),
                render_hint,
                created_at,
            ),
        )

    def _assert_owned(self, connection: sqlite3.Connection, public_id: str, user_id: str) -> None:
        row = connection.execute(
            "SELECT user_id FROM runtime_runs WHERE public_id = ?",
            (public_id,),
        ).fetchone()
        if row is None:
            raise KeyError(public_id)
        if row["user_id"] != user_id:
            raise LedgerOwnershipError("Run does not belong to the current user.")

    @staticmethod
    def _active_count(connection: sqlite3.Connection, field: str, value: str) -> int:
        row = connection.execute(
            f"SELECT COUNT(*) AS value FROM runtime_runs WHERE {field} = ? "
            "AND status NOT IN ('completed', 'failed', 'cancelled', 'interrupted')",
            (value,),
        ).fetchone()
        return int(row["value"] if row else 0)

    @staticmethod
    def _reservation_count(connection: sqlite3.Connection, field: str, value: str) -> int:
        row = connection.execute(
            f"SELECT COUNT(*) AS value FROM runtime_admissions WHERE {field} = ?",
            (value,),
        ).fetchone()
        return int(row["value"] if row else 0)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _object(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {"succeeded": "completed", "success": "completed", "stopped": "cancelled"}
    return aliases.get(normalized, normalized or "accepted")


def _status_from_event(event_name: str, _payload: dict[str, Any]) -> str | None:
    if event_name.startswith("run."):
        return _normalize_status(event_name.split(".", 1)[1])
    return None


def _workflow_artifact(workflow: str) -> tuple[str, str, str]:
    return {
        "progressive-hint": ("answer_card", "Progressive hint", "markdown"),
        "error-diagnosis": ("diagnosis_report", "Error diagnosis", "diagnosis"),
        "training-plan": ("training_plan", "Training plan", "plan"),
        "learning-profile": ("learning_profile_review", "Learning profile review", "markdown"),
    }.get(workflow, ("run_summary", "Agent response", "markdown"))
