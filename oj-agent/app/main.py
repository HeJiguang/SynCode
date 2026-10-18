from fastapi import FastAPI, HTTPException, status

from app.agent_runtime.factory import build_agent_runtime
from app.api.training import router as training_router
from app.core.config import load_settings


app = FastAPI(title="SynCode Training Planner", version="1.0.0")


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "UP"}


@app.get("/ready", include_in_schema=False)
def ready() -> dict[str, str]:
    try:
        build_agent_runtime(load_settings())
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "NOT_READY", "reason": str(exc)},
        ) from exc
    return {"status": "READY"}


app.include_router(training_router)
