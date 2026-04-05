from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.remote_db_config import RemoteDatabaseConfig


@dataclass(slots=True)
class RemoteConnectionResult:
    ok: bool
    message: str


class RemoteDatabaseConfigService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_config(self) -> RemoteDatabaseConfig | None:
        return (
            self.session.query(RemoteDatabaseConfig)
            .filter(RemoteDatabaseConfig.is_active.is_(True))
            .order_by(RemoteDatabaseConfig.config_id.desc())
            .first()
        )

    def save_active_config(
        self,
        *,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        dialect: str = "mysql+pymysql",
        charset: str = "utf8mb4",
        name: str = "default",
    ) -> RemoteDatabaseConfig:
        config = self.get_active_config()
        if config is None:
            config = RemoteDatabaseConfig()
        config.name = name
        config.dialect = dialect
        config.host = host
        config.port = port
        config.database_name = database_name
        config.username = username
        config.password = password
        config.charset = charset
        config.is_active = True
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def build_database_url(self, config: RemoteDatabaseConfig) -> str:
        if config.dialect == "sqlite":
            return f"sqlite:///{config.database_name}"
        user = quote_plus(config.username)
        password = quote_plus(config.password)
        return (
            f"{config.dialect}://{user}:{password}@{config.host}:{config.port}/"
            f"{config.database_name}?charset={config.charset}"
        )

    def test_connection(self, config: RemoteDatabaseConfig) -> RemoteConnectionResult:
        database_url = self.build_database_url(config)
        try:
            engine = create_engine(database_url, future=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.execute(text("SELECT 1 FROM tb_question LIMIT 1"))
        except Exception as exc:
            return RemoteConnectionResult(ok=False, message=str(exc))
        return RemoteConnectionResult(ok=True, message="连接成功，已确认可访问 tb_question。")
