from __future__ import annotations

from dataclasses import replace

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.llm_config import LLMConfig


class LLMConfigService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_config(self) -> LLMConfig | None:
        return (
            self.session.query(LLMConfig)
            .filter(LLMConfig.is_active.is_(True))
            .order_by(LLMConfig.config_id.desc())
            .first()
        )

    def save_active_config(
        self,
        *,
        enabled: bool,
        base_url: str,
        api_key: str,
        model: str,
        name: str = "default",
    ) -> LLMConfig:
        config = self.get_active_config()
        if config is None:
            config = LLMConfig()
        config.name = name
        config.enabled = enabled
        config.base_url = base_url or None
        config.api_key = api_key or None
        config.model = model or None
        config.is_active = True
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def apply_to_settings(self, settings: Settings) -> Settings:
        config = self.get_active_config()
        if config is None:
            return settings
        return replace(
            settings,
            llm_enabled=config.enabled,
            llm_base_url=config.base_url,
            llm_api_key=config.api_key,
            llm_model=config.model,
        )
