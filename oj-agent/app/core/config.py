from dataclasses import dataclass
import os
from pathlib import Path
import socket
from typing import Any
from urllib.parse import quote_plus

from app.core.nacos_config import load_nacos_config as _load_nacos_config
import yaml

# 核心细节：使用 pathlib.Path(__file__).resolve() 动态获取当前文件的绝对路径，
# 然后向上找两级目录 (parents[2]) 定位到项目的根目录。
# 这样做的好处是：无论你在哪个目录下执行启动命令，程序都能精准找到资源文件，不会报“找不到路径”的错误。
DEFAULT_RAG_DOC_GLOB = str(
    Path(__file__).resolve().parents[2] / "resources" / "knowledge" / "algorithm-docs" / "*.md"
)
DEFAULT_RUNTIME_DATA_DIR = str(
    Path(__file__).resolve().parents[2] / "runtime-artifacts"
)


# 核心细节：@dataclass(frozen=True) 定义了一个“不可变 (Immutable)”的数据类。
# 一旦 AgentSettings 被实例化，程序运行期间任何地方试图修改这些配置（例如 settings.port = 8080）都会直接抛出异常。
# 这是极其重要的防御性编程设计，防止配置在运行中途被意外篡改导致难以排查的幽灵 Bug。
@dataclass(frozen=True)
class AgentSettings:
    """
    全局配置聚合模型 (AgentSettings)
    """
    port: int
    llm_provider: str
    llm_base_url: str | None
    llm_api_key: str | None
    chat_model: str | None
    training_model: str | None
    embedding_provider: str
    embedding_model: str | None
    embedding_dimensions: int
    llm_timeout_seconds: float
    llm_temperature: float
    llm_max_tokens: int
    llm_enabled: bool
    gateway_user_id_header: str
    rag_enabled: bool
    rag_doc_globs: tuple[str, ...]
    rag_top_k: int
    rag_max_snippet_chars: int
    qdrant_enabled: bool
    qdrant_url: str | None
    qdrant_api_key: str | None
    qdrant_collection: str
    qdrant_top_k: int
    qdrant_chunk_size: int
    nacos_config_enabled: bool
    nacos_config_data_id: str
    nacos_enabled: bool
    nacos_server_addr: str | None
    nacos_namespace: str | None
    nacos_group: str
    nacos_username: str | None
    nacos_password: str | None
    nacos_service_name: str
    nacos_ip: str
    nacos_port: int
    runtime_data_dir: str = DEFAULT_RUNTIME_DATA_DIR
    trace_store_backend: str = "memory"
    query_ledger_store_backend: str = "memory"
    evaluation_store_backend: str = "memory"
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
    auth_base_url: str | None = None
    allow_insecure_user_id_body: bool = False
    conversation_soft_token_limit: int = 16000
    conversation_hard_token_limit: int = 22000
    user_max_active_runs: int = 3
    user_run_rate_limit_per_minute: int = 20
    active_run_stale_seconds: float = 300.0
    global_max_concurrent_runs: int = 16
    run_admission_wait_seconds: float = 15.0


def _to_bool(raw: str | bool | None, default: bool) -> bool:
    """
    安全地将各种各样的输入转换为布尔值。
    工程痛点：环境变量读进来的永远是字符串，"true", "1", "yes" 在业务逻辑里都应该算作 True。
    """
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_file() -> None:
    """
    手动加载 .env 文件并将变量注入到 os.environ 中。
    通常用于本地开发环境，避免在系统里到处配置环境变量。
    """
    env_file = os.getenv("OJ_AGENT_ENV_FILE")
    if not env_file:
        return

    path = Path(env_file)
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        # 忽略空行和注释行 (#)
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        # 核心细节：如果环境变量里已经有这个 key 了，就不覆盖它。
        # 优先级：系统真实环境变量 > .env 文件
        if key and key not in os.environ:
            os.environ[key] = value


def _nested(config: dict[str, Any], *keys: str) -> Any:
    """
    安全地从嵌套字典中读取值（例如从解析好的 YAML 字典中）。
    比如 _nested(config, "llm", "api-key") 等同于 config.get("llm", {}).get("api-key")
    但写法更优雅，且遇到中间层级缺失时不会报 KeyError。
    """
    current: Any = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


# 下面四个 _read_xxx 函数是统一读取配置的工具。
# 它们强制执行了系统的一套优先级规则：
# 1. 优先读取 os.getenv (环境变量/容器注入的值)
# 2. 如果环境变量没有，再读 Nacos 或本地 YAML 的嵌套值 (config)
# 3. 如果都没有，使用代码里写死的 default 默认值

def _read_str(config: dict[str, Any], env_key: str, path: tuple[str, ...], default: str | None = None) -> str | None:
    raw = os.getenv(env_key)
    if raw is not None:
        return raw
    value = _nested(config, *path)
    if value is None:
        return default
    return str(value)


def _read_bool(config: dict[str, Any], env_key: str, path: tuple[str, ...], default: bool) -> bool:
    raw = os.getenv(env_key)
    if raw is not None:
        return _to_bool(raw, default)
    value = _nested(config, *path)
    return _to_bool(value, default)


def _read_int(config: dict[str, Any], env_key: str, path: tuple[str, ...], default: int) -> int:
    raw = os.getenv(env_key)
    if raw is not None:
        return int(raw)
    value = _nested(config, *path)
    return int(value) if value is not None else default


def _read_float(config: dict[str, Any], env_key: str, path: tuple[str, ...], default: float) -> float:
    raw = os.getenv(env_key)
    if raw is not None:
        return float(raw)
    value = _nested(config, *path)
    return float(value) if value is not None else default


def _read_globs(config: dict[str, Any]) -> tuple[str, ...]:
    """
    专门用来处理 RAG (检索增强生成) 的文档路径通配符读取。
    支持用分号 ";" 隔开多个路径。
    """
    raw = os.getenv("OJ_AGENT_RAG_DOC_GLOBS")
    if raw:
        parts = [item.strip() for item in raw.split(";") if item.strip()]
        return tuple(parts)

    value = _nested(config, "rag", "doc-globs")
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        if parts:
            return tuple(parts)

    if isinstance(value, str) and value.strip():
        return tuple(item.strip() for item in value.split(";") if item.strip())

    return (DEFAULT_RAG_DOC_GLOB,)


def _resolve_default_nacos_ip() -> str:
    explicit = os.getenv("HOST_IP")
    if explicit:
        return explicit

    hostname_ip = os.getenv("HOSTNAME")
    if hostname_ip:
        try:
            resolved = socket.gethostbyname(hostname_ip)
            if resolved and not resolved.startswith("127."):
                return resolved
        except OSError:
            pass

    server_addr = os.getenv("OJ_AGENT_NACOS_SERVER_ADDR")
    if server_addr:
        host = server_addr.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((host, 8848))
                resolved = sock.getsockname()[0]
                if resolved:
                    return resolved
        except OSError:
            pass

    try:
        resolved = socket.gethostbyname(socket.gethostname())
        if resolved:
            return resolved
    except OSError:
        pass

    return "127.0.0.1"


def _build_database_url(runtime_data_dir: str, nacos_config: dict[str, Any]) -> str:
    explicit = _read_str(nacos_config, "OJ_AGENT_DATABASE_URL", ("database", "url"))
    if explicit:
        return explicit

    mysql_host = os.getenv("MYSQL_HOST")
    mysql_database = os.getenv("MYSQL_DATABASE")
    mysql_user = os.getenv("MYSQL_APP_USER") or os.getenv("SPRING_DATASOURCE_USERNAME")
    mysql_password = os.getenv("MYSQL_PASSWORD") or os.getenv("SPRING_DATASOURCE_PASSWORD")
    mysql_port = os.getenv("MYSQL_PORT", "3306")
    if all((mysql_host, mysql_database, mysql_user, mysql_password)):
        return (
            "mysql+pymysql://"
            f"{quote_plus(str(mysql_user))}:{quote_plus(str(mysql_password))}"
            f"@{mysql_host}:{mysql_port}/{mysql_database}?charset=utf8mb4"
        )

    database_path = Path(runtime_data_dir) / "syncode-agent.sqlite3"
    return f"sqlite+pysqlite:///{database_path}"


def load_settings() -> AgentSettings:
    """
    全局配置加载入口函数。
    在程序启动或构建工厂函数时被调用，返回一个冻结的 AgentSettings 对象。
    """
    # 1. 尝试加载本地环境变量文件
    _load_env_file()
    
    # 2. 从 Nacos 配置中心拉取配置
    nacos_payload = _load_nacos_config()
    nacos_config = dict(nacos_payload.get("data") or {})
    
    # 3. 如果 Nacos 返回的是纯文本的 YAML 格式，则解析它
    if not nacos_config and nacos_payload.get("raw"):
        parsed = yaml.safe_load(str(nacos_payload["raw"])) or {}
        if isinstance(parsed, dict):
            nacos_config = parsed

    # 4. 按优先级依次解析所有具体的配置项
    port = _read_int(nacos_config, "OJ_AGENT_PORT", ("server", "port"), 8015)
    llm_api_key = _read_str(nacos_config, "OJ_AGENT_LLM_API_KEY", ("llm", "api-key"))
    chat_model = _read_str(nacos_config, "OJ_AGENT_CHAT_MODEL", ("llm", "chat-model"))
    training_model = _read_str(nacos_config, "OJ_AGENT_TRAINING_MODEL", ("llm", "training-model"))
    embedding_provider = _read_str(nacos_config, "OJ_AGENT_EMBEDDING_PROVIDER", ("llm", "embedding-provider"), "openai_compatible")
    embedding_model = _read_str(nacos_config, "OJ_AGENT_EMBEDDING_MODEL", ("llm", "embedding-model"))
    embedding_dimensions = _read_int(nacos_config, "OJ_AGENT_EMBEDDING_DIMENSIONS", ("llm", "embedding-dimensions"), 256)
    agent_runtime_provider = _read_str(
        nacos_config,
        "OJ_AGENT_RUNTIME_PROVIDER",
        ("agent-runtime", "provider"),
        "direct",
    ) or "direct"
    runtime_data_dir = _read_str(
        nacos_config,
        "OJ_AGENT_RUNTIME_DATA_DIR",
        ("runtime", "data-dir"),
        DEFAULT_RUNTIME_DATA_DIR,
    ) or DEFAULT_RUNTIME_DATA_DIR

    # 5. 实例化并返回最终的配置对象
    return AgentSettings(
        port=port,
        llm_provider=_read_str(nacos_config, "OJ_AGENT_LLM_PROVIDER", ("llm", "provider"), "openai_compatible") or "openai_compatible",
        llm_base_url=_read_str(nacos_config, "OJ_AGENT_LLM_BASE_URL", ("llm", "base-url")),
        llm_api_key=llm_api_key,
        chat_model=chat_model,
        training_model=training_model,
        embedding_provider=embedding_provider or "openai_compatible",
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
        llm_timeout_seconds=_read_float(nacos_config, "OJ_AGENT_LLM_TIMEOUT_SECONDS", ("llm", "timeout-seconds"), 30.0),
        llm_temperature=_read_float(nacos_config, "OJ_AGENT_LLM_TEMPERATURE", ("llm", "temperature"), 0.2),
        llm_max_tokens=_read_int(nacos_config, "OJ_AGENT_LLM_MAX_TOKENS", ("llm", "max-tokens"), 1200),
        
        # 动态推断开关：如果有 API Key 且配置了模型，则自动认为大模型功能可用
        llm_enabled=bool(llm_api_key and (chat_model or training_model)),
        
        gateway_user_id_header=_read_str(nacos_config, "OJ_AGENT_GATEWAY_USER_ID_HEADER", ("agent", "gateway-user-id-header"), "X-User-Id") or "X-User-Id",
        rag_enabled=_read_bool(nacos_config, "OJ_AGENT_RAG_ENABLED", ("rag", "enabled"), True),
        rag_doc_globs=_read_globs(nacos_config),
        rag_top_k=_read_int(nacos_config, "OJ_AGENT_RAG_TOP_K", ("rag", "top-k"), 3),
        rag_max_snippet_chars=_read_int(nacos_config, "OJ_AGENT_RAG_MAX_SNIPPET_CHARS", ("rag", "max-snippet-chars"), 420),
        qdrant_enabled=_read_bool(nacos_config, "OJ_AGENT_QDRANT_ENABLED", ("qdrant", "enabled"), False),
        qdrant_url=_read_str(nacos_config, "OJ_AGENT_QDRANT_URL", ("qdrant", "url")),
        qdrant_api_key=_read_str(nacos_config, "OJ_AGENT_QDRANT_API_KEY", ("qdrant", "api-key")),
        qdrant_collection=_read_str(nacos_config, "OJ_AGENT_QDRANT_COLLECTION", ("qdrant", "collection"), "oj-agent-knowledge") or "oj-agent-knowledge",
        qdrant_top_k=_read_int(nacos_config, "OJ_AGENT_QDRANT_TOP_K", ("qdrant", "top-k"), 3),
        qdrant_chunk_size=_read_int(nacos_config, "OJ_AGENT_QDRANT_CHUNK_SIZE", ("qdrant", "chunk-size"), 240),
        runtime_data_dir=runtime_data_dir,
        trace_store_backend=_read_str(nacos_config, "OJ_AGENT_TRACE_STORE", ("runtime", "trace-store"), "memory") or "memory",
        query_ledger_store_backend=_read_str(nacos_config, "OJ_AGENT_QUERY_LEDGER_STORE", ("runtime", "query-ledger-store"), "memory") or "memory",
        evaluation_store_backend=_read_str(nacos_config, "OJ_AGENT_EVALUATION_STORE", ("runtime", "evaluation-store"), "memory") or "memory",
        agent_runtime_provider=agent_runtime_provider,
        agent_runtime_fallback_to_direct=_read_bool(
            nacos_config,
            "OJ_AGENT_RUNTIME_FALLBACK_TO_DIRECT",
            ("agent-runtime", "fallback-to-direct"),
            True,
        ),
        hermes_base_url=_read_str(
            nacos_config,
            "OJ_AGENT_HERMES_BASE_URL",
            ("agent-runtime", "hermes", "base-url"),
        ),
        hermes_api_key=_read_str(
            nacos_config,
            "OJ_AGENT_HERMES_API_KEY",
            ("agent-runtime", "hermes", "api-key"),
        ),
        hermes_provider=_read_str(
            nacos_config,
            "OJ_AGENT_HERMES_PROVIDER",
            ("agent-runtime", "hermes", "provider"),
            "deepseek",
        ) or "deepseek",
        hermes_chat_model=_read_str(
            nacos_config,
            "OJ_AGENT_HERMES_CHAT_MODEL",
            ("agent-runtime", "hermes", "chat-model"),
        ),
        hermes_training_model=_read_str(
            nacos_config,
            "OJ_AGENT_HERMES_TRAINING_MODEL",
            ("agent-runtime", "hermes", "training-model"),
        ),
        hermes_request_timeout_seconds=_read_float(
            nacos_config,
            "OJ_AGENT_HERMES_REQUEST_TIMEOUT_SECONDS",
            ("agent-runtime", "hermes", "request-timeout-seconds"),
            10.0,
        ),
        hermes_run_timeout_seconds=_read_float(
            nacos_config,
            "OJ_AGENT_HERMES_RUN_TIMEOUT_SECONDS",
            ("agent-runtime", "hermes", "run-timeout-seconds"),
            90.0,
        ),
        hermes_poll_interval_seconds=_read_float(
            nacos_config,
            "OJ_AGENT_HERMES_POLL_INTERVAL_SECONDS",
            ("agent-runtime", "hermes", "poll-interval-seconds"),
            0.25,
        ),
        database_url=_build_database_url(runtime_data_dir, nacos_config),
        auth_base_url=_read_str(
            nacos_config,
            "OJ_AGENT_AUTH_BASE_URL",
            ("agent", "auth-base-url"),
        ),
        allow_insecure_user_id_body=_read_bool(
            nacos_config,
            "OJ_AGENT_ALLOW_INSECURE_USER_ID_BODY",
            ("agent", "allow-insecure-user-id-body"),
            False,
        ),
        conversation_soft_token_limit=_read_int(
            nacos_config,
            "OJ_AGENT_CONVERSATION_SOFT_TOKEN_LIMIT",
            ("conversation", "soft-token-limit"),
            16000,
        ),
        conversation_hard_token_limit=_read_int(
            nacos_config,
            "OJ_AGENT_CONVERSATION_HARD_TOKEN_LIMIT",
            ("conversation", "hard-token-limit"),
            22000,
        ),
        user_max_active_runs=_read_int(
            nacos_config,
            "OJ_AGENT_USER_MAX_ACTIVE_RUNS",
            ("run-limits", "user-max-active-runs"),
            3,
        ),
        user_run_rate_limit_per_minute=_read_int(
            nacos_config,
            "OJ_AGENT_USER_RUN_RATE_LIMIT_PER_MINUTE",
            ("run-limits", "user-run-rate-limit-per-minute"),
            20,
        ),
        active_run_stale_seconds=_read_float(
            nacos_config,
            "OJ_AGENT_ACTIVE_RUN_STALE_SECONDS",
            ("run-limits", "active-run-stale-seconds"),
            300.0,
        ),
        global_max_concurrent_runs=_read_int(
            nacos_config,
            "OJ_AGENT_GLOBAL_MAX_CONCURRENT_RUNS",
            ("run-limits", "global-max-concurrent-runs"),
            16,
        ),
        run_admission_wait_seconds=_read_float(
            nacos_config,
            "OJ_AGENT_RUN_ADMISSION_WAIT_SECONDS",
            ("run-limits", "admission-wait-seconds"),
            15.0,
        ),
        nacos_config_enabled=_to_bool(os.getenv("OJ_AGENT_NACOS_CONFIG_ENABLED"), bool(os.getenv("OJ_AGENT_NACOS_SERVER_ADDR"))),
        nacos_config_data_id=os.getenv("OJ_AGENT_NACOS_CONFIG_DATA_ID", "oj-agent-local.yaml"),
        nacos_enabled=_read_bool(nacos_config, "OJ_AGENT_NACOS_ENABLED", ("nacos", "enabled"), False),
        nacos_server_addr=os.getenv("OJ_AGENT_NACOS_SERVER_ADDR"),
        nacos_namespace=os.getenv("OJ_AGENT_NACOS_NAMESPACE") or _read_str(nacos_config, "OJ_AGENT_NACOS_NAMESPACE", ("nacos", "namespace")),
        nacos_group=os.getenv("OJ_AGENT_NACOS_GROUP", _read_str(nacos_config, "OJ_AGENT_NACOS_GROUP", ("nacos", "group"), "DEFAULT_GROUP") or "DEFAULT_GROUP"),
        nacos_username=os.getenv("OJ_AGENT_NACOS_USERNAME"),
        nacos_password=os.getenv("OJ_AGENT_NACOS_PASSWORD"),
        nacos_service_name=_read_str(nacos_config, "OJ_AGENT_NACOS_SERVICE_NAME", ("nacos", "service-name"), "oj-agent") or "oj-agent",
        nacos_ip=_read_str(nacos_config, "OJ_AGENT_NACOS_IP", ("nacos", "ip"), _resolve_default_nacos_ip()) or _resolve_default_nacos_ip(),
        nacos_port=_read_int(nacos_config, "OJ_AGENT_NACOS_PORT", ("nacos", "port"), port),
    )
