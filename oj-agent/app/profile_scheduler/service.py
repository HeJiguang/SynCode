from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import os
from typing import Any

import httpx

from app.mcp_gateway.repository import LearningRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SchedulerSettings:
    gateway_base_url: str
    gateway_key: str
    poll_interval_seconds: int = 900
    batch_size: int = 500
    max_runs_per_sweep: int = 5

    @classmethod
    def from_env(cls) -> "SchedulerSettings":
        return cls(
            gateway_base_url=_required("SYNCODE_AGENT_RUNTIME_BASE_URL").rstrip("/"),
            gateway_key=_required("SYNCODE_AGENT_RUNTIME_GATEWAY_KEY"),
            poll_interval_seconds=_bounded_int(
                "SYNCODE_LEARNING_PROFILE_POLL_SECONDS",
                default=900,
                minimum=60,
                maximum=86400,
            ),
            batch_size=_bounded_int(
                "SYNCODE_LEARNING_PROFILE_BATCH_SIZE",
                default=500,
                minimum=1,
                maximum=5000,
            ),
            max_runs_per_sweep=_bounded_int(
                "SYNCODE_LEARNING_PROFILE_MAX_RUNS_PER_SWEEP",
                default=5,
                minimum=1,
                maximum=100,
            ),
        )


class LearningProfileScheduler:
    def __init__(
        self,
        settings: SchedulerSettings,
        repository: LearningRepository,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.client = client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None
        self.last_sweep_at: str | None = None
        self.last_result: dict[str, Any] = {
            "sources": 0,
            "scheduled": 0,
            "unchanged": 0,
            "failed": 0,
        }

    async def sweep(self) -> dict[str, int]:
        sources = self.repository.list_learning_profile_sources(self.settings.batch_size)
        result = {"sources": len(sources), "scheduled": 0, "unchanged": 0, "failed": 0}
        for source in sources:
            if result["scheduled"] >= self.settings.max_runs_per_sweep:
                break
            try:
                response = await self.client.post(
                    f"{self.settings.gateway_base_url}/internal/learning-profile-refreshes",
                    headers={"Authorization": f"Bearer {self.settings.gateway_key}"},
                    json=source,
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("scheduled") is True:
                    result["scheduled"] += 1
                else:
                    result["unchanged"] += 1
            except (httpx.HTTPError, ValueError, TypeError):
                result["failed"] += 1
                logger.exception("Learning profile refresh trigger failed for user %s", source.get("user_id"))
        self.last_sweep_at = datetime.now(timezone.utc).isoformat()
        self.last_result = result
        return result

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.sweep()
            except Exception:
                logger.exception("Learning profile scheduler sweep failed")
                self.last_sweep_at = datetime.now(timezone.utc).isoformat()
                self.last_result = {"sources": 0, "scheduled": 0, "unchanged": 0, "failed": 1}
            try:
                await asyncio.wait_for(stop.wait(), timeout=self.settings.poll_interval_seconds)
            except TimeoutError:
                continue

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()
        self.repository.close()


def _required(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    if "\n" in value or "\r" in value:
        raise RuntimeError(f"Invalid newline in setting: {name}")
    return value


def _bounded_int(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = (os.getenv(name) or "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer setting: {name}") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}.")
    return value
