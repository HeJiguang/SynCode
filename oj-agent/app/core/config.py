from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import quote_plus


DEFAULT_RUNTIME_DATA_DIR = str(Path(__file__).resolve().parents[2] / "runtime-artifacts")


@dataclass(frozen=True)
class AgentSettings:
    port: int = 8015
    llm_provider: str = "openai_compatible"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    chat_model: str | None = None
    training_model: str | None = None
    llm_timeout_seconds: float = 30.0
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1200
    llm_enabled: bool = False
    runtime_data_dir: str = DEFAULT_RUNTIME_DATA_DIR
    agent_runtime_provider: str = "direct"
    agent_runtime_fallback_to_direct: bool = True
    hermes_base_url: str | None = None
    hermes_api_key: str | None = None
    hermes_provider: str = "deepseek"
    hermes_chat_model: str | None = None
    hermes_training_model: str | None = None
    hermes_request_timeout_seconds: float = 10.0
    hermes_run_timeout_seconds: float = 90.0
    hermes_poll_interval_seconds: float = 0.25
    database_url: str | None = None


def _load_env_file() -> None:
    path_value = os.getenv("OJ_AGENT_ENV_FILE")
    if not path_value:
        return
    path = Path(path_value)
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip():
            os.environ.setdefault(key.strip(), value.strip())


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def _database_url(runtime_data_dir: str) -> str:
    explicit = os.getenv("OJ_AGENT_DATABASE_URL")
    if explicit:
        return explicit
    host = os.getenv("MYSQL_HOST")
    database = os.getenv("MYSQL_DATABASE")
    user = os.getenv("MYSQL_APP_USER") or os.getenv("SPRING_DATASOURCE_USERNAME")
    password = os.getenv("MYSQL_PASSWORD") or os.getenv("SPRING_DATASOURCE_PASSWORD")
    port = os.getenv("MYSQL_PORT", "3306")
    if all((host, database, user, password)):
        return (
            f"mysql+pymysql://{quote_plus(str(user))}:{quote_plus(str(password))}"
            f"@{host}:{port}/{database}?charset=utf8mb4"
        )
    return f"sqlite+pysqlite:///{Path(runtime_data_dir) / 'syncode-agent.sqlite3'}"


def load_settings() -> AgentSettings:
    _load_env_file()
    runtime_data_dir = os.getenv("OJ_AGENT_RUNTIME_DATA_DIR", DEFAULT_RUNTIME_DATA_DIR)
    llm_api_key = os.getenv("OJ_AGENT_LLM_API_KEY")
    chat_model = os.getenv("OJ_AGENT_CHAT_MODEL")
    training_model = os.getenv("OJ_AGENT_TRAINING_MODEL")
    return AgentSettings(
        port=_int("OJ_AGENT_PORT", 8015),
        llm_provider=os.getenv("OJ_AGENT_LLM_PROVIDER", "openai_compatible"),
        llm_base_url=os.getenv("OJ_AGENT_LLM_BASE_URL"),
        llm_api_key=llm_api_key,
        chat_model=chat_model,
        training_model=training_model,
        llm_timeout_seconds=_float("OJ_AGENT_LLM_TIMEOUT_SECONDS", 30.0),
        llm_temperature=_float("OJ_AGENT_LLM_TEMPERATURE", 0.2),
        llm_max_tokens=_int("OJ_AGENT_LLM_MAX_TOKENS", 1200),
        llm_enabled=bool(llm_api_key and (chat_model or training_model)),
        runtime_data_dir=runtime_data_dir,
        agent_runtime_provider=os.getenv("OJ_AGENT_RUNTIME_PROVIDER", "direct"),
        agent_runtime_fallback_to_direct=_bool("OJ_AGENT_RUNTIME_FALLBACK_TO_DIRECT", True),
        hermes_base_url=os.getenv("OJ_AGENT_HERMES_BASE_URL"),
        hermes_api_key=os.getenv("OJ_AGENT_HERMES_API_KEY"),
        hermes_provider=os.getenv("OJ_AGENT_HERMES_PROVIDER", "deepseek"),
        hermes_chat_model=os.getenv("OJ_AGENT_HERMES_CHAT_MODEL"),
        hermes_training_model=os.getenv("OJ_AGENT_HERMES_TRAINING_MODEL"),
        hermes_request_timeout_seconds=_float("OJ_AGENT_HERMES_REQUEST_TIMEOUT_SECONDS", 10.0),
        hermes_run_timeout_seconds=_float("OJ_AGENT_HERMES_RUN_TIMEOUT_SECONDS", 90.0),
        hermes_poll_interval_seconds=_float("OJ_AGENT_HERMES_POLL_INTERVAL_SECONDS", 0.25),
        database_url=_database_url(runtime_data_dir),
    )
