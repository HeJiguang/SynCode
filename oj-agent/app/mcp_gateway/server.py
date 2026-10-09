from __future__ import annotations

from contextlib import asynccontextmanager
import hmac
import os

from fastapi import FastAPI, Header, HTTPException, status
from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import load_settings
from app.mcp_gateway.identity import resolve_tool_identity
from app.mcp_gateway.profiles import HermesProfileProvisioner, ProfileProvisionError
from app.mcp_gateway.repository import LearningRepository


mcp = FastMCP("SynCode Learning Tools")
_repository: LearningRepository | None = None
READ_ONLY_TOOL = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}
CONTROLLED_WRITE_TOOL = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": False,
    "openWorldHint": False,
}


class TrainingPlanTaskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    recommended_reason: str = Field(min_length=1, max_length=500)
    due_time: str | None = None


def repository() -> LearningRepository:
    global _repository
    if _repository is None:
        settings = load_settings()
        if not settings.database_url:
            raise RuntimeError("OJ agent database is not configured.")
        _repository = LearningRepository(settings.database_url)
    return _repository


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_question(question_id: str) -> dict | None:
    """Read the public statement and metadata for one SynCode question."""
    resolve_tool_identity()
    return repository().get_question(question_id)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_my_submission_history(question_id: str, limit: int = 5) -> list[dict]:
    """Read the current user's recent submissions for one question, including code and judge diagnostics."""
    identity = resolve_tool_identity()
    return repository().get_submission_history(identity.user_id, question_id, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_my_recent_submissions(limit: int = 20) -> list[dict]:
    """Read the current user's recent submissions across questions without exposing other users."""
    identity = resolve_tool_identity()
    return repository().get_recent_submissions(identity.user_id, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_my_learning_profile() -> dict:
    """Read the current user's solved/submission counts and saved training profile."""
    identity = resolve_tool_identity()
    return repository().get_learning_profile(identity.user_id)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_my_current_training_plan() -> dict | None:
    """Read the current user's active or pending training plan and its tasks."""
    identity = resolve_tool_identity()
    return repository().get_current_training_plan(identity.user_id)


@mcp.tool(annotations=READ_ONLY_TOOL)
def search_practice_questions(
    knowledge_tag: str | None = None,
    difficulty: int | None = None,
    exclude_solved: bool = True,
    limit: int = 10,
) -> list[dict]:
    """Find enabled practice questions for the current user with bounded tag and difficulty filters."""
    identity = resolve_tool_identity()
    return repository().search_practice_questions(
        identity.user_id,
        knowledge_tag=knowledge_tag,
        difficulty=difficulty,
        exclude_solved=exclude_solved,
        limit=limit,
    )


@mcp.tool(annotations=CONTROLLED_WRITE_TOOL)
def save_my_training_plan(
    plan_title: str,
    plan_goal: str,
    tasks: list[TrainingPlanTaskInput],
    ai_summary: str | None = None,
) -> dict:
    """Save an approved training plan for the current user using real SynCode questions."""
    identity = resolve_tool_identity()
    return repository().save_training_plan(
        identity.user_id,
        plan_title=plan_title,
        plan_goal=plan_goal,
        tasks=[task.model_dump() for task in tasks],
        ai_summary=ai_summary,
    )


@mcp.tool(annotations=CONTROLLED_WRITE_TOOL)
def update_my_training_task(task_id: str, task_status: int = 1) -> dict:
    """Mark one owned training task pending (0), completed (1), or skipped (2)."""
    identity = resolve_tool_identity()
    return repository().update_training_task(identity.user_id, task_id, task_status)


@mcp.tool(annotations=CONTROLLED_WRITE_TOOL)
def record_my_recommendation_feedback(
    recommendation_id: str,
    action: str,
    question_id: str | None = None,
    run_id: str | None = None,
) -> dict:
    """Record an approved impression, open, acceptance, or skip for a recommendation shown to the current user."""
    identity = resolve_tool_identity()
    return repository().record_recommendation_feedback(
        identity.user_id,
        recommendation_id=recommendation_id,
        action=action,
        question_id=question_id,
        run_id=run_id,
    )


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_my_training_effects(plan_id: str | None = None) -> dict:
    """Measure attempts, completions and passes for the current user's latest or selected plan."""
    identity = resolve_tool_identity()
    return repository().get_training_effects(identity.user_id, plan_id)


class ProfileRequest(BaseModel):
    user_id: str
    profile: str


mcp_app = mcp.http_app(path="/", stateless_http=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp_app.lifespan(_app):
        yield
    global _repository
    if _repository is not None:
        _repository.close()
        _repository = None


app = FastAPI(title="SynCode Hermes Tools", version="1.0.0", lifespan=lifespan)
app.mount("/mcp", mcp_app)


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "UP"}


@app.post("/internal/profiles/ensure")
def ensure_profile(
    request: ProfileRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, str | bool]:
    expected = (os.getenv("SYNCODE_HERMES_PROVISION_KEY") or "").strip()
    supplied = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else ""
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid provision credential.")
    try:
        created = HermesProfileProvisioner().ensure(user_id=request.user_id, profile=request.profile)
    except (ProfileProvisionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"profile": request.profile, "created": created}
