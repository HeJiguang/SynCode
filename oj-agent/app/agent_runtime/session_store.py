import hashlib
import json
import logging
from pathlib import Path
from threading import Lock

from app.core.jsonl_store import append_jsonl


LOGGER = logging.getLogger(__name__)


class HermesSessionStore:
    """Durable mapping between a SynCode conversation and its Hermes session."""

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "hermes-sessions.jsonl"
        self._lock = Lock()
        self._sessions = self._load()

    @staticmethod
    def conversation_key(user_id: str, conversation_id: str) -> str:
        raw = f"{user_id}\0{conversation_id}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def get(self, user_id: str, conversation_id: str) -> str | None:
        key = self.conversation_key(user_id, conversation_id)
        with self._lock:
            return self._sessions.get(key)

    def bind(self, user_id: str, conversation_id: str, session_id: str) -> None:
        key = self.conversation_key(user_id, conversation_id)
        with self._lock:
            if self._sessions.get(key) == session_id:
                return
            self._sessions[key] = session_id
            try:
                append_jsonl(self.path, {"conversation_key": key, "session_id": session_id})
            except OSError:
                LOGGER.warning("Failed to persist Hermes session mapping.", exc_info=True)

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}

        sessions: dict[str, str] = {}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        row = json.loads(line)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    key = row.get("conversation_key") if isinstance(row, dict) else None
                    session_id = row.get("session_id") if isinstance(row, dict) else None
                    if isinstance(key, str) and isinstance(session_id, str):
                        sessions[key] = session_id
        except OSError:
            LOGGER.warning("Failed to load Hermes session mappings.", exc_info=True)
        return sessions
