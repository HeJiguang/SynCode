from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.core.config import load_settings
from app.mcp_gateway.repository import LearningRepository
from app.profile_scheduler.service import LearningProfileScheduler, SchedulerSettings


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_settings = load_settings()
    if not agent_settings.database_url:
        raise RuntimeError("OJ agent database is not configured.")
    scheduler = LearningProfileScheduler(
        SchedulerSettings.from_env(),
        LearningRepository(agent_settings.database_url),
    )
    stop = asyncio.Event()
    task = asyncio.create_task(scheduler.run(stop), name="learning-profile-scheduler")
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        stop.set()
        await task
        await scheduler.close()


app = FastAPI(title="SynCode Learning Profile Scheduler", version="1.0.0", lifespan=lifespan)


@app.get("/health", include_in_schema=False)
def health(request: Request) -> dict:
    scheduler: LearningProfileScheduler = request.app.state.scheduler
    return {
        "status": "UP",
        "last_sweep_at": scheduler.last_sweep_at,
        "last_result": scheduler.last_result,
    }
