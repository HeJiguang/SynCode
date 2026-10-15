from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hmac
import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, status
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from app.core.config import load_settings
from app.learning_memory.repository import LearningMemoryRepository
from app.learning_memory.service import LearningMemoryService
from app.learning_memory.state_service import LearningStateService
from app.mcp_gateway.identity import ToolIdentityError, resolve_tool_identity, user_id_from_profile
from app.mcp_gateway.profiles import HermesProfileProvisioner, ProfileProvisionError
from app.mcp_gateway.repository import LearningRepository
from app.skill_governance.models import (
    GovernanceHeartbeatRequest,
    LifecycleReviewRequest,
    PromotionReviewRequest,
    UserSkillMutationRequest,
    UserSkillRequest,
    UserSkillRollbackRequest,
)
from app.skill_governance.repository import SkillGovernanceRepository
from app.skill_governance.search import SkillSearchError
from app.skill_governance.service import SkillGovernanceService
from app.skill_governance.storage import SkillStorageError
from app.skill_governance.usage import SkillUsageBatch, SkillUsageRepository


mcp = FastMCP("SynCode Learning Tools")
_repository: LearningRepository | None = None
_usage_repository: SkillUsageRepository | None = None
_governance_repository: SkillGovernanceRepository | None = None
_governance_service: SkillGovernanceService | None = None
_learning_memory_repository: LearningMemoryRepository | None = None
_learning_memory_service: LearningMemoryService | None = None
_learning_state_service: LearningStateService | None = None
log = logging.getLogger(__name__)
READ_ONLY_TOOL = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}
_PRODUCTION_TABLES = (
    "tb_ai_skill",
    "tb_ai_skill_version",
    "tb_ai_skill_promotion_candidate",
    "tb_ai_skill_promotion_member",
    "tb_ai_skill_promotion_review_action",
    "tb_ai_skill_release",
    "tb_ai_skill_lifecycle_review",
    "tb_ai_skill_governance_heartbeat",
    "tb_ai_skill_usage_event",
    "tb_ai_learning_memory",
    "tb_ai_learning_memory_evidence",
    "tb_ai_learning_memory_projection_state",
    "tb_ai_learning_state_memory",
    "tb_ai_learning_state_evidence",
    "tb_ai_learning_state_projection",
)


def repository() -> LearningRepository:
    global _repository
    if _repository is None:
        settings = load_settings()
        if not settings.database_url:
            raise RuntimeError("OJ agent database is not configured.")
        _repository = LearningRepository(settings.database_url)
    return _repository


def usage_repository() -> SkillUsageRepository:
    global _usage_repository
    if _usage_repository is None:
        settings = load_settings()
        if not settings.database_url:
            raise RuntimeError("OJ agent database is not configured.")
        _usage_repository = SkillUsageRepository(settings.database_url)
    return _usage_repository


def governance_service() -> SkillGovernanceService:
    global _governance_repository, _governance_service
    if _governance_service is None:
        settings = load_settings()
        if not settings.database_url:
            raise RuntimeError("OJ agent database is not configured.")
        _governance_repository = SkillGovernanceRepository(settings.database_url)
        _governance_service = SkillGovernanceService(_governance_repository)
    return _governance_service


def learning_memory_service() -> LearningMemoryService:
    global _learning_memory_repository, _learning_memory_service
    if _learning_memory_service is None:
        settings = load_settings()
        if not settings.database_url:
            raise RuntimeError("OJ agent database is not configured.")
        _learning_memory_repository = LearningMemoryRepository(settings.database_url)
        _learning_memory_service = LearningMemoryService(_learning_memory_repository)
    return _learning_memory_service


def learning_state_service() -> LearningStateService:
    global _learning_state_service
    if _learning_state_service is None:
        memory_service = learning_memory_service()
        _learning_state_service = LearningStateService(memory_service.repository, memory_service)
    return _learning_state_service


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


def _recall_learning_memory(
    *,
    user_id: str,
    query: str,
    levels: list[str] | None = None,
    knowledge_tags: list[str] | None = None,
    time_range_days: int = 90,
    pattern_limit: int = 3,
    episode_limit: int = 5,
    event_limit: int = 5,
) -> dict:
    return learning_memory_service().recall(
        user_id=user_id,
        query=query,
        levels=levels,
        knowledge_tags=knowledge_tags,
        time_range_days=time_range_days,
        pattern_limit=pattern_limit,
        episode_limit=episode_limit,
        event_limit=event_limit,
    )


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_my_learning_memory_detail(memory_id: str) -> dict:
    """Expand one recalled problem-solving memory into its structured facts and source evidence."""
    identity = resolve_tool_identity()
    return learning_memory_service().detail(user_id=identity.user_id, memory_id=memory_id)


def _recall_learning_state_memory(
    *,
    user_id: str,
    knowledge_tags: list[str] | None = None,
    focus: Literal["weakest", "review_due", "improving", "declining", "all"] = "weakest",
    limit: int = 10,
) -> dict:
    return learning_state_service().recall(
        user_id=user_id,
        knowledge_tags=knowledge_tags,
        focus=focus,
        limit=limit,
    )


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_my_learning_state_memory_detail(state_id: str) -> dict:
    """Expand one learning-state memory into its scoring facts and supporting problem-solving episodes."""
    identity = resolve_tool_identity()
    return learning_state_service().detail(user_id=identity.user_id, state_id=state_id)


class ProfileRequest(BaseModel):
    user_id: str
    profile: str


class LearningMemoryRecallRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


mcp_app = mcp.http_app(path="/", stateless_http=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    heartbeat_task = None
    if (os.getenv("SYNCODE_SKILL_GOVERNANCE_HEARTBEAT_ENABLED") or "").strip().lower() in {
        "1", "true", "yes", "on"
    }:
        heartbeat_task = asyncio.create_task(_governance_heartbeat_loop())
    async with mcp_app.lifespan(_app):
        yield
    if heartbeat_task is not None:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    global _repository
    if _repository is not None:
        _repository.close()
        _repository = None
    global _usage_repository
    if _usage_repository is not None:
        _usage_repository.close()
        _usage_repository = None
    global _governance_repository, _governance_service
    if _governance_repository is not None:
        _governance_repository.close()
        _governance_repository = None
        _governance_service = None
    global _learning_memory_repository, _learning_memory_service, _learning_state_service
    if _learning_memory_repository is not None:
        _learning_memory_repository.close()
        _learning_memory_repository = None
        _learning_memory_service = None
        _learning_state_service = None


async def _governance_heartbeat_loop() -> None:
    interval = max(300, int(os.getenv("SYNCODE_SKILL_GOVERNANCE_HEARTBEAT_SECONDS", "3600")))
    await asyncio.sleep(min(60, interval))
    while True:
        try:
            await asyncio.to_thread(governance_service().heartbeat)
        except Exception:
            log.exception("Skill governance heartbeat failed")
        try:
            await asyncio.to_thread(learning_state_service().sync_all)
        except Exception:
            log.exception("Learning memory projection heartbeat failed")
        await asyncio.sleep(interval)


app = FastAPI(title="SynCode Hermes Tools", version="1.0.0", lifespan=lifespan)
app.mount("/mcp", mcp_app)


def _require_internal_credential(authorization: str | None, detail: str) -> None:
    expected = (os.getenv("SYNCODE_HERMES_PROVISION_KEY") or "").strip()
    supplied = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else ""
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "UP"}


def _database_schema_check(engine) -> tuple[bool, str]:
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
            for table in _PRODUCTION_TABLES:
                connection.exec_driver_sql(f"SELECT 1 FROM `{table}` LIMIT 0")
    except Exception as exc:
        return False, f"database schema unavailable: {type(exc).__name__}"
    return True, "database schema ready"


def _production_config_check() -> tuple[bool, str]:
    strict = (os.getenv("SYNCODE_PRODUCTION_READINESS_STRICT") or "").strip().lower() in {
        "1", "true", "yes", "on"
    }
    if not strict:
        return True, "strict production configuration disabled"
    settings = load_settings()
    if not str(settings.database_url or "").startswith("mysql+"):
        return False, "production database must use MySQL"
    required = (
        "SYNCODE_ELASTICSEARCH_URL",
        "SYNCODE_SKILL_EMBEDDING_URL",
        "SYNCODE_SKILL_EMBEDDING_MODEL",
        "SYNCODE_SKILL_EMBEDDING_DIMENSIONS",
        "SYNCODE_MCP_SERVICE_KEY",
        "SYNCODE_HERMES_PROVISION_KEY",
        "HERMES_API_SERVER_KEY",
    )
    missing = []
    for name in required:
        value = (os.getenv(name) or "").strip()
        if not value or "REPLACE" in value.upper() or value.lower().startswith("replace-with"):
            missing.append(name)
    if missing:
        return False, f"missing production settings: {', '.join(missing)}"
    embedding_url = os.environ["SYNCODE_SKILL_EMBEDDING_URL"].strip()
    if embedding_url != "local://fastembed":
        embedding_api_key = (os.getenv("SYNCODE_SKILL_EMBEDDING_API_KEY") or "").strip()
        if not embedding_api_key or "REPLACE" in embedding_api_key.upper():
            return False, "missing production settings: SYNCODE_SKILL_EMBEDDING_API_KEY"
    try:
        if int(os.environ["SYNCODE_SKILL_EMBEDDING_DIMENSIONS"]) <= 0:
            raise ValueError
    except (KeyError, ValueError):
        return False, "SYNCODE_SKILL_EMBEDDING_DIMENSIONS must be positive"
    return True, "production configuration ready"


def _platform_store_check() -> tuple[bool, str]:
    path = Path(
        os.getenv("SYNCODE_PLATFORM_SKILL_STORE", "/var/lib/hermes/platform-skills")
    )
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".readiness-probe"
        probe.write_text("ready", encoding="ascii")
        probe.unlink()
    except OSError as exc:
        return False, f"platform Skill store unavailable: {type(exc).__name__}"
    return True, "platform Skill store writable"


@app.get("/ready", include_in_schema=False)
def ready() -> dict:
    checks: dict[str, str] = {}
    config_ok, checks["configuration"] = _production_config_check()
    store_ok, checks["platform_store"] = _platform_store_check()
    try:
        database_ok, checks["database"] = _database_schema_check(governance_service().repository.engine)
    except Exception as exc:
        database_ok = False
        checks["database"] = f"database initialization failed: {type(exc).__name__}"
    if not all((config_ok, store_ok, database_ok)):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "NOT_READY", "checks": checks},
        )
    return {"status": "READY", "checks": checks}


def _resolve_learning_memory_identity(
    authorization: str | None,
    profile: str | None,
) -> str:
    expected = (os.getenv("SYNCODE_MCP_SERVICE_KEY") or "").strip()
    supplied = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else ""
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid learning-memory credential.")
    try:
        return user_id_from_profile(profile or "")
    except ToolIdentityError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Hermes profile identity.",
        ) from exc


def _build_learning_memory_context(*, user_id: str, query: str) -> dict:
    problem_solving = _recall_learning_memory(
        user_id=user_id,
        query=query,
        levels=["pattern", "episode", "event"],
        time_range_days=180,
        pattern_limit=2,
        episode_limit=4,
        event_limit=2,
    )
    knowledge_tags: list[str] = []
    for group in ("patterns", "episodes", "events"):
        for memory in problem_solving.get(group) or []:
            for tag in memory.get("knowledge_tags") or []:
                normalized = str(tag).strip()
                if normalized and normalized not in knowledge_tags:
                    knowledge_tags.append(normalized)
    learning_state = _recall_learning_state_memory(
        user_id=user_id,
        knowledge_tags=knowledge_tags[:10] or None,
        focus="all" if knowledge_tags else "weakest",
        limit=5,
    )
    return {
        "memory_domain": "syncode_learning",
        "query": query,
        "problem_solving": problem_solving,
        "learning_state": learning_state,
    }


@app.post("/internal/learning-memory/recall", include_in_schema=False)
def recall_learning_memory_context(
    request: LearningMemoryRecallRequest,
    authorization: str | None = Header(default=None),
    profile: str | None = Header(default=None, alias="X-SynCode-Hermes-Profile"),
) -> dict:
    user_id = _resolve_learning_memory_identity(authorization, profile)
    try:
        return _build_learning_memory_context(user_id=user_id, query=request.query.strip())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/internal/profiles/ensure")
def ensure_profile(
    request: ProfileRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, str | bool]:
    _require_internal_credential(authorization, "Invalid provision credential.")
    try:
        created = HermesProfileProvisioner().ensure(user_id=request.user_id, profile=request.profile)
    except (ProfileProvisionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    try:
        governance_service().sync_user(user_id=request.user_id, profile=request.profile)
    except Exception:
        log.exception("Personal Skill synchronization failed for %s", request.profile)
    return {"profile": request.profile, "created": created}


@app.post("/internal/skill-governance/users/sync")
def sync_user_skills(
    request: UserSkillRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().sync_user(user_id=request.user_id, profile=request.profile)
    except (ValueError, SkillStorageError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/internal/skill-governance/users/{user_id}/skills")
def list_user_skills(
    user_id: str,
    authorization: str | None = Header(default=None),
) -> list[dict]:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().list_user_skills(user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/internal/skill-governance/users/{user_id}/skills/{skill_name}/versions")
def list_user_skill_versions(
    user_id: str,
    skill_name: str,
    authorization: str | None = Header(default=None),
) -> list[dict]:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().repository.list_personal_versions(
            user_id=user_id,
            skill_name=skill_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/internal/skill-governance/users/archive")
def archive_user_skill(
    request: UserSkillMutationRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().archive_user_skill(
            user_id=request.user_id,
            profile=request.profile,
            name=request.skill_name,
        )
    except (ValueError, SkillStorageError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/internal/skill-governance/users/restore")
def restore_user_skill(
    request: UserSkillMutationRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().restore_user_skill(
            user_id=request.user_id,
            profile=request.profile,
            name=request.skill_name,
        )
    except (ValueError, SkillStorageError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/internal/skill-governance/users/rollback")
def rollback_user_skill(
    request: UserSkillRollbackRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().rollback_user_skill(
            user_id=request.user_id,
            profile=request.profile,
            name=request.skill_name,
            version=request.version,
        )
    except (ValueError, SkillStorageError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/internal/skill-governance/heartbeat")
def run_skill_governance_heartbeat(
    request: GovernanceHeartbeatRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().heartbeat(
            min_distinct_owners=request.min_distinct_owners,
            neighbor_limit=request.neighbor_limit,
        )
    except (ValueError, SkillStorageError, SkillSearchError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/internal/skill-governance/candidates")
def list_promotion_candidates(
    candidate_status: str = "reviewing",
    limit: int = 50,
    authorization: str | None = Header(default=None),
) -> list[dict]:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().repository.list_promotion_candidates(
            status=candidate_status,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/internal/skill-governance/candidates/{candidate_id}")
def get_promotion_candidate(
    candidate_id: str,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().repository.promotion_candidate(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post("/internal/skill-governance/candidates/{candidate_id}/review")
def review_promotion_candidate(
    candidate_id: str,
    request: PromotionReviewRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().review_promotion(
            candidate_id=candidate_id,
            reviewer=request.reviewer,
            decision=request.decision,
            note=request.note,
            proposed_skill_name=request.proposed_skill_name,
            category=request.category,
            content=request.content,
        )
    except (ValueError, SkillStorageError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/internal/skill-governance/lifecycle-reviews")
def list_skill_lifecycle_reviews(
    review_status: str = "pending",
    limit: int = 50,
    authorization: str | None = Header(default=None),
) -> list[dict]:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().repository.list_lifecycle_reviews(
            status=review_status,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/internal/skill-governance/lifecycle-reviews/{review_id}")
def review_skill_lifecycle(
    review_id: str,
    request: LifecycleReviewRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_internal_credential(authorization, "Invalid Skill governance credential.")
    try:
        return governance_service().review_lifecycle(
            review_id=review_id,
            reviewer=request.reviewer,
            decision=request.decision,
            note=request.note,
        )
    except (ValueError, SkillStorageError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/internal/skill-events")
def record_skill_events(
    batch: SkillUsageBatch,
    authorization: str | None = Header(default=None),
) -> dict[str, int]:
    _require_internal_credential(authorization, "Invalid telemetry credential.")
    if batch.profile != f"syncode-u{batch.user_id}":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telemetry profile does not match user.")
    try:
        inserted, duplicates = usage_repository().record_events(
            user_id=batch.user_id,
            profile=batch.profile,
            events=batch.events,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"accepted": inserted, "duplicates": duplicates}
