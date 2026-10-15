from fastapi import FastAPI

from app.api.training import router as training_router


app = FastAPI(title="SynCode Training Planner", version="1.0.0")


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "UP"}


app.include_router(training_router)
