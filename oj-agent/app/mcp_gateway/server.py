from __future__ import annotations

from contextlib import asynccontextmanager
import hmac
import os

from fastapi import FastAPI, Header, HTTPException, status
from fastmcp import FastMCP
from pydantic import BaseModel

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
