from contextlib import contextmanager
from datetime import timedelta
from threading import BoundedSemaphore, Lock
import math
from typing import Iterator

from app.application.run_service import RunService
from app.conversations.repository import utc_now
from app.core.config import AgentSettings, load_settings
from app.domain.runs import ContextRef, EventType, Run, RunSource, RunStatus, RunType


class RunAdmissionError(RuntimeError):
    status_code = 409

    def __init__(self, message: str, *, run_id: str, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.run_id = run_id
        self.retry_after_seconds = retry_after_seconds


class RunRateLimitExceeded(RunAdmissionError):
    status_code = 429


class RunExecutionSlotTimeout(RuntimeError):
    def __init__(self, *, wait_seconds: float) -> None:
        super().__init__("Agent 执行资源已满，请稍后重试。")
        self.retry_after_seconds = max(1, math.ceil(wait_seconds))


def create_admitted_run(
    service: RunService,
    *,
    run_type: RunType,
    source: RunSource,
    user_id: str,
    conversation_id: str | None,
    context_ref: ContextRef,
    request_payload: dict,
    queue_for_execution: bool,
) -> Run:
    settings = load_settings()
    now = utc_now()

    with service.run_store.user_admission_lock(user_id):
        active_limit = max(0, settings.user_max_active_runs)
        rate_limit = max(0, settings.user_run_rate_limit_per_minute)
        active_count = service.run_store.count_active_runs(
            user_id,
            stale_before=now - timedelta(seconds=max(0.0, settings.active_run_stale_seconds)),
        )
        recent_count = service.run_store.count_runs_since(user_id, since=now - timedelta(minutes=1))

        rejection_reason: str | None = None
        if active_limit and active_count >= active_limit:
            rejection_reason = f"当前用户已有 {active_count} 个活跃 Agent Run，最多允许 {active_limit} 个。"
        elif rate_limit and recent_count >= rate_limit:
            rejection_reason = f"当前用户每分钟最多创建 {rate_limit} 个 Agent Run。"

        if rejection_reason is not None:
            run = service.create_run(
                run_type=run_type,
                source=source,
                user_id=user_id,
                conversation_id=conversation_id,
                context_ref=context_ref,
                request_payload=request_payload,
                initial_status=RunStatus.FAILED,
            )
            service.append_event(
                run.run_id,
                EventType.RESOURCE_LIMIT_REJECTED,
                {
                    "reason": rejection_reason,
                    "activeRuns": active_count,
                    "recentRuns": recent_count,
                },
            )
            service.mark_failed(run.run_id, reason=rejection_reason, active_node="run_admission")
            error_class = (
                RunRateLimitExceeded
                if rate_limit and recent_count >= rate_limit and not (active_limit and active_count >= active_limit)
                else RunAdmissionError
            )
            raise error_class(rejection_reason, run_id=run.run_id, retry_after_seconds=60)

        return service.create_run(
            run_type=run_type,
            source=source,
            user_id=user_id,
            conversation_id=conversation_id,
            context_ref=context_ref,
            request_payload=request_payload,
            initial_status=RunStatus.QUEUED if queue_for_execution else RunStatus.ACCEPTED,
        )


class RunExecutionSlotLimiter:
    def __init__(self) -> None:
        self._guard = Lock()
        self._semaphores: dict[int, BoundedSemaphore] = {}

    @contextmanager
    def slot(self, settings: AgentSettings | None = None) -> Iterator[None]:
        resolved = settings or load_settings()
        maximum = max(0, resolved.global_max_concurrent_runs)
        if maximum == 0:
            yield
            return

        semaphore = self._semaphore_for(maximum)
        wait_seconds = max(0.0, resolved.run_admission_wait_seconds)
        if not semaphore.acquire(timeout=wait_seconds):
            raise RunExecutionSlotTimeout(wait_seconds=wait_seconds)
        try:
            yield
        finally:
            semaphore.release()

    def _semaphore_for(self, maximum: int) -> BoundedSemaphore:
        with self._guard:
            semaphore = self._semaphores.get(maximum)
            if semaphore is None:
                semaphore = BoundedSemaphore(maximum)
                self._semaphores[maximum] = semaphore
            return semaphore


run_execution_slot_limiter = RunExecutionSlotLimiter()
