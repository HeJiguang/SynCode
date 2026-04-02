from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.artifacts import router as artifacts_router
from app.api.drafts import router as drafts_router
from app.api.inbox import router as inbox_router
from app.api.runs import router as runs_router
from app.api.training import router as training_router
from app.core.config import load_settings
from app.core.nacos_registry import NacosRegistry
from app.retrieval.routes.dense import bootstrap_dense_index


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = load_settings()
    registry = NacosRegistry(settings)

    # Keep local startup tolerant when Nacos is unavailable.
    try:
        registry.register()
    except Exception:
        pass

    # Dense retrieval bootstrap should not block local development.
    try:
        bootstrap_dense_index()
    except Exception:
        pass

    try:
        yield
    finally:
        try:
            registry.deregister()
        except Exception:
            pass


app = FastAPI(title="OJ Agent", version="0.1.0", lifespan=lifespan)
app.include_router(training_router)
app.include_router(runs_router)
app.include_router(inbox_router)
app.include_router(drafts_router)
app.include_router(artifacts_router)
