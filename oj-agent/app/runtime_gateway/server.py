from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import hmac
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict

from app.runtime_gateway.adapters import (
    RuntimeAdapterError,
    RuntimeContext,
    RuntimeResponse,
    create_adapter,
)
from app.runtime_gateway.ids import PublicIdError, decode_public_id, encode_public_id
from app.runtime_gateway.ledger import (
    AdmissionLimitExceeded,
    LedgerOwnershipError,
    ProfileRefreshBusy,
    RuntimeLedger,
)
from app.runtime_gateway.registry import (
    RegistryError,
    RuntimeConflictError,
    RuntimeNotFoundError,
    RuntimeRegistry,
    RuntimeSpec,
)


@dataclass(frozen=True, slots=True)
class GatewaySettings:
    gateway_key: str
    registry_path: Path
    default_name: str
    default_spec: RuntimeSpec | None
    ledger_path: Path | None = None
    max_concurrent_runs_per_user: int = 2
    max_concurrent_runs_per_runtime: int = 20
    run_stale_after_seconds: int = 3600
    auto_failover: bool = True

    @classmethod
    def from_env(cls) -> "GatewaySettings":
        registry_path = Path(os.getenv("SYNCODE_RUNTIME_REGISTRY_PATH", "/var/lib/syncode-runtime/registry.json"))
        default_adapter = (os.getenv("SYNCODE_RUNTIME_DEFAULT_ADAPTER") or "").strip()
        default_base_url = (os.getenv("SYNCODE_RUNTIME_DEFAULT_BASE_URL") or "").strip()
        default_api_key = (os.getenv("SYNCODE_RUNTIME_DEFAULT_API_KEY") or "").strip()
        default_provision_url = (os.getenv("SYNCODE_RUNTIME_DEFAULT_PROVISION_URL") or "").strip()
        default_provision_key = (os.getenv("SYNCODE_RUNTIME_DEFAULT_PROVISION_KEY") or "").strip()
        default_spec = None
        if default_adapter or default_base_url or default_api_key or default_provision_url or default_provision_key:
            default_spec = RuntimeSpec(
                adapter=default_adapter or _required_env("SYNCODE_RUNTIME_DEFAULT_ADAPTER"),
                base_url=default_base_url or _required_env("SYNCODE_RUNTIME_DEFAULT_BASE_URL"),
                api_key=default_api_key or _required_env("SYNCODE_RUNTIME_DEFAULT_API_KEY"),
                provision_url=default_provision_url or None,
                provision_key=default_provision_key or None,
            )
        return cls(
            gateway_key=_required_env("SYNCODE_RUNTIME_GATEWAY_KEY"),
            registry_path=registry_path,
            default_name=os.getenv("SYNCODE_RUNTIME_DEFAULT_NAME", "hermes").strip(),
            default_spec=default_spec,
            ledger_path=Path(
                os.getenv(
                    "SYNCODE_RUNTIME_LEDGER_PATH",
                    str(registry_path.parent / "runtime-ledger.sqlite3"),
                )
            ),
            max_concurrent_runs_per_user=_env_int("SYNCODE_RUNTIME_MAX_RUNS_PER_USER", 2, minimum=0),
            max_concurrent_runs_per_runtime=_env_int("SYNCODE_RUNTIME_MAX_RUNS_PER_RUNTIME", 20, minimum=0),
            run_stale_after_seconds=_env_int("SYNCODE_RUNTIME_RUN_STALE_SECONDS", 3600, minimum=60),
            auto_failover=_env_bool("SYNCODE_RUNTIME_AUTO_FAILOVER", True),
        )


class RuntimeRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter: str
    base_url: str
    api_key: str
    provision_url: str | None = None
    provision_key: str | None = None

    def spec(self) -> RuntimeSpec:
        return RuntimeSpec(**self.model_dump())


class LearningProfileRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    source_watermark: str


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved = settings or GatewaySettings.from_env()
        app.state.gateway_settings = resolved
        app.state.runtime_registry = RuntimeRegistry(
            resolved.registry_path,
            resolved.default_name,
            resolved.default_spec,
        )
        ledger_path = resolved.ledger_path or resolved.registry_path.parent / "runtime-ledger.sqlite3"
        app.state.runtime_ledger = RuntimeLedger(
            ledger_path,
            per_user_limit=resolved.max_concurrent_runs_per_user,
            per_runtime_limit=resolved.max_concurrent_runs_per_runtime,
            stale_after_seconds=resolved.run_stale_after_seconds,
        )
        try:
            yield
        finally:
            app.state.runtime_ledger.close()

    gateway = FastAPI(title="SynCode Agent Runtime Gateway", version="1.0.0", lifespan=lifespan)

    @gateway.get("/health", include_in_schema=False)
    def health(request: Request) -> dict[str, str]:
        registry = _registry(request)
        active, _ = registry.active_runtime()
        return {"status": "UP", "active_runtime": active}

    @gateway.get("/internal/runtimes", dependencies=[Depends(_authorize)])
    def list_runtimes(request: Request) -> dict[str, Any]:
        snapshot = _registry(request).snapshot()
        return {
            "active": snapshot.active,
            "runtimes": {
                name: {**spec.public(), "active": name == snapshot.active}
                for name, spec in sorted(snapshot.runtimes.items())
            },
        }

    @gateway.put("/internal/runtimes/{name}", dependencies=[Depends(_authorize)])
    def register_runtime(name: str, registration: RuntimeRegistration, request: Request) -> JSONResponse:
        try:
            created = _registry(request).register(name, registration.spec())
        except RuntimeConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except (RegistryError, PublicIdError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return JSONResponse({"name": name, "created": created}, status_code=201 if created else 200)

    @gateway.post("/internal/runtimes/{name}/activate", dependencies=[Depends(_authorize)])
    async def activate_runtime(name: str, request: Request) -> dict[str, str | bool]:
        registry = _registry(request)
        try:
            spec = registry.runtime(name)
        except (RuntimeNotFoundError, PublicIdError) as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if not await create_adapter(spec).health():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Candidate Runtime failed its health check; active Runtime was not changed.",
            )
        changed = registry.activate(name)
        return {"active": name, "changed": changed}

    @gateway.get("/v1/sessions")
    async def list_sessions(
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> Response:
        snapshot = _registry(request).snapshot()
        rows: list[dict[str, Any]] = []
        warnings: list[dict[str, str]] = []
        upstream_limit = min(max(limit + offset, 200), 1000)

        async def load(name: str, spec: RuntimeSpec) -> tuple[str, RuntimeResponse | None, str | None]:
            try:
                upstream = await create_adapter(spec).list_sessions(context, upstream_limit)
                if not 200 <= upstream.status_code < 300:
                    raise RuntimeAdapterError(f"Runtime returned HTTP {upstream.status_code}.")
                return name, upstream, None
            except (RuntimeAdapterError, RegistryError, ValueError) as exc:
                return name, None, str(exc)

        results = await asyncio.gather(*(load(name, spec) for name, spec in snapshot.runtimes.items()))
        for name, upstream, error in results:
            if error is not None or upstream is None:
                if name == snapshot.active:
                    return JSONResponse(
                        {"message": "The active Agent Runtime is unavailable."},
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )
                warnings.append({"runtime": name, "message": error or "Runtime is unavailable."})
                continue
            try:
                payload = _json_object(upstream)
                native_rows = payload.get("data", [])
                if not isinstance(native_rows, list):
                    raise RuntimeAdapterError("Runtime returned an invalid session list.")
                for item in native_rows:
                    if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                        continue
                    row = dict(item)
                    row["id"] = encode_public_id("session", name, item["id"])
                    row["runtime"] = name
                    rows.append(row)
            except (RuntimeAdapterError, RegistryError, ValueError) as exc:
                if name == snapshot.active:
                    return JSONResponse(
                        {"message": "The active Agent Runtime is unavailable."},
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )
                warnings.append({"runtime": name, "message": str(exc)})
        rows.sort(key=_session_sort_key, reverse=True)
        return JSONResponse({"data": rows[offset : offset + limit], "total": len(rows), "warnings": warnings})

    @gateway.post("/v1/sessions")
    async def create_session(request: Request, context: RuntimeContext = Depends(_runtime_context)) -> Response:
        body = await request.body()
        name, upstream, degraded_from = await _call_new_resource_with_failover(
            request,
            lambda spec: create_adapter(spec).create_session(context, body),
        )
        return _rewrite_json_response(
            upstream,
            lambda payload: _with_failover_metadata(
                _rewrite_session_response(payload, name),
                runtime_name=name,
                degraded_from=degraded_from,
            ),
        )

    @gateway.patch("/v1/sessions/{session_id}")
    async def update_session(
        session_id: str,
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        name, native_id, spec = _resolve_resource(request, session_id, "session")
        upstream = await _adapter_call(create_adapter(spec).update_session(context, native_id, await request.body()))
        return _rewrite_json_response(upstream, lambda payload: _rewrite_session_response(payload, name))

    @gateway.get("/v1/sessions/{session_id}/messages")
    async def list_messages(
        session_id: str,
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        name, native_id, spec = _resolve_resource(request, session_id, "session")
        upstream = await _adapter_call(
            create_adapter(spec).list_messages(context, native_id, request.url.query)
        )
        return _rewrite_json_response(upstream, lambda payload: _rewrite_named_ids(payload, name))

    @gateway.post("/v1/runs")
    async def create_run(request: Request, context: RuntimeContext = Depends(_runtime_context)) -> Response:
        try:
            payload = json.loads(await request.body())
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body must be JSON.") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body must be an object.")
        return await _create_run_for_payload(request, context, payload)

    @gateway.post(
        "/internal/learning-profile-refreshes",
        dependencies=[Depends(_authorize)],
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def schedule_learning_profile_refresh(
        refresh: LearningProfileRefreshRequest,
        request: Request,
    ) -> Response:
        if not refresh.user_id.isdigit():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Runtime user identity.")
        watermark = refresh.source_watermark.strip()
        if (
            not watermark
            or len(watermark) > 160
            or any(ord(char) < 33 or ord(char) > 126 for char in watermark)
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source watermark.")
        await _refresh_scheduled_profile_run(request, refresh.user_id, watermark)
        try:
            profile_reservation = _ledger(request).reserve_profile_refresh(refresh.user_id, watermark)
        except ProfileRefreshBusy:
            return JSONResponse(
                {"scheduled": False, "reason": "in_progress", "source_watermark": watermark},
                status_code=status.HTTP_200_OK,
            )
        if profile_reservation is None:
            return JSONResponse(
                {"scheduled": False, "reason": "unchanged", "source_watermark": watermark},
                status_code=status.HTTP_200_OK,
            )
        context = RuntimeContext(
            user_id=refresh.user_id,
            session_key=f"syncode-learning-profile-{refresh.user_id}",
        )
        try:
            response = await _create_run_for_payload(
                request,
                context,
                {
                    "workflow": "learning-profile",
                    "input": (
                        "根据受控工具中的最新学习数据更新学习画像。"
                        f"本次数据水位为 {watermark}。严格按 Skill 执行，只生成需要用户审核的 USER.md 候选。"
                    ),
                },
            )
            if not 200 <= response.status_code < 300:
                _ledger(request).release_profile_refresh(profile_reservation)
                return response
            scheduled = json.loads(response.body)
            run_id = scheduled.get("run_id")
            runtime_name = scheduled.get("runtime")
            if not isinstance(run_id, str) or not isinstance(runtime_name, str):
                raise RuntimeAdapterError("Runtime Gateway returned an invalid scheduled run.")
            _ledger(request).commit_profile_refresh(
                profile_reservation,
                run_public_id=run_id,
                runtime_name=runtime_name,
            )
            return JSONResponse(
                {
                    "scheduled": True,
                    "source_watermark": watermark,
                    "run_id": run_id,
                    "session_id": scheduled.get("session_id"),
                    "runtime": runtime_name,
                    "degraded_from": scheduled.get("degraded_from"),
                },
                status_code=status.HTTP_202_ACCEPTED,
            )
        except BaseException:
            _ledger(request).release_profile_refresh(profile_reservation)
            raise

    @gateway.get("/v1/runs/{run_id}/events")
    async def run_events(
        run_id: str,
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
        last_seq: int | None = Query(default=None, ge=-1),
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    ) -> Response:
        name, native_id, spec = _resolve_resource(request, run_id, "run")
        if last_event_id is not None and (len(last_event_id) > 32 or not last_event_id.isdigit()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid SSE event cursor.")
        cursor = max(last_seq if last_seq is not None else -1, int(last_event_id) if last_event_id else -1)
        try:
            stored_events = _ledger(request).list_events(run_id, context.user_id, after=cursor)
            terminal = _ledger(request).has_terminal_event(run_id, context.user_id)
        except KeyError:
            stored_events = []
            terminal = False
        except LedgerOwnershipError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        replay_cursor = max(
            [cursor, *(int(event["sequence_no"]) for event in stored_events)],
        )
        stored_cursor = max([-1, *(int(event["sequence_no"]) for event in stored_events)])
        upstream_last_seq = max(last_seq if last_seq is not None else -1, stored_cursor)
        upstream_last_event_id = last_event_id
        if stored_cursor >= 0 and (upstream_last_event_id is None or int(upstream_last_event_id) < stored_cursor):
            upstream_last_event_id = str(stored_cursor)
        terminal = terminal or any(
            event["event"] in {"run.completed", "run.failed", "run.cancelled", "run.interrupted"}
            for event in stored_events
        )
        upstream = None
        if not terminal:
            try:
                upstream = await create_adapter(spec).run_events(
                    context,
                    native_id,
                    last_seq=upstream_last_seq if upstream_last_seq >= 0 else None,
                    last_event_id=upstream_last_event_id,
                )
            except RuntimeAdapterError as exc:
                if not stored_events:
                    return JSONResponse({"message": str(exc)}, status_code=status.HTTP_502_BAD_GATEWAY)
        if upstream is not None and not 200 <= upstream.status_code < 300:
            content = await upstream.bytes()
            content_type = upstream.content_type
            status_code = upstream.status_code
            await upstream.close()
            if stored_events:
                upstream = None
            else:
                return Response(content, status_code=status_code, media_type=content_type)

        async def stream() -> AsyncIterator[bytes]:
            for stored in stored_events:
                yield (stored["frame"] + "\n\n").encode("utf-8")
            if upstream is None:
                return
            frame: list[str] = []
            try:
                async for line in upstream.lines():
                    if line == "":
                        rewritten = _rewrite_sse_frame(frame, name)
                        _persist_sse_frame(request, context, run_id, rewritten)
                        yield (rewritten + "\n\n").encode("utf-8")
                        frame = []
                    else:
                        frame.append(line)
                if frame:
                    rewritten = _rewrite_sse_frame(frame, name)
                    _persist_sse_frame(request, context, run_id, rewritten)
                    yield (rewritten + "\n\n").encode("utf-8")
            finally:
                await upstream.close()

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @gateway.get("/v1/runs/{run_id}")
    async def get_run(
        run_id: str,
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        name, native_id, spec = _resolve_resource(request, run_id, "run")
        try:
            stored = _ledger(request).get_run(run_id, context.user_id)
        except LedgerOwnershipError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        try:
            upstream = await create_adapter(spec).get_run(context, native_id)
        except RuntimeAdapterError:
            if stored is not None:
                return JSONResponse({**stored, "runtime_available": False})
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Agent Runtime is unavailable.")
        if not 200 <= upstream.status_code < 300:
            if stored is not None and upstream.status_code >= 500:
                return JSONResponse({**stored, "runtime_available": False})
            return _rewrite_json_response(upstream, lambda payload: _rewrite_named_ids(payload, name))
        payload = _rewrite_named_ids(_json_object(upstream), name)
        if isinstance(payload, dict):
            try:
                _ledger(request).update_run(run_id, context.user_id, payload)
            except KeyError:
                pass
        return JSONResponse(payload, status_code=upstream.status_code)

    @gateway.get("/v1/runs/{run_id}/artifacts")
    async def list_run_artifacts(
        run_id: str,
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        _resolve_resource(request, run_id, "run")
        try:
            artifacts = _ledger(request).list_artifacts(run_id, context.user_id)
        except KeyError:
            return JSONResponse({"data": [], "total": 0})
        except LedgerOwnershipError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return JSONResponse({"data": artifacts, "total": len(artifacts)})

    @gateway.post("/v1/runs/{run_id}/{action}")
    async def control_run(
        run_id: str,
        action: str,
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        if action not in {"approval", "steer", "stop"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported run control action.")
        name, native_id, spec = _resolve_resource(request, run_id, "run")
        try:
            _ledger(request).get_run(run_id, context.user_id)
        except LedgerOwnershipError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        upstream = await _adapter_call(
            create_adapter(spec).control_run(context, native_id, action, await request.body() or b"{}")
        )
        return _rewrite_json_response(upstream, lambda payload: _rewrite_named_ids(payload, name))

    @gateway.get("/v1/memories")
    async def list_memories(
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        return await _aggregate_runtime_lists(
            request,
            context,
            lambda adapter: adapter.list_memories(context),
            _rewrite_memory_document,
        )

    @gateway.get("/v1/memory-candidates")
    async def list_memory_candidates(
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        return await _aggregate_runtime_lists(
            request,
            context,
            lambda adapter: adapter.list_memory_candidates(context),
            _rewrite_memory_candidate,
        )

    @gateway.post("/v1/memory-candidates/{candidate_id}/{action}")
    async def review_memory_candidate(
        candidate_id: str,
        action: str,
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        if action not in {"approve", "reject"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported memory review action.")
        name, native_id, spec = _resolve_resource(request, candidate_id, "memory_candidate")
        upstream = await _adapter_call(
            create_adapter(spec).review_memory_candidate(context, native_id, action)
        )
        return _rewrite_json_response(
            upstream,
            lambda payload: _rewrite_memory_review_response(payload, name),
        )

    @gateway.get("/v1/context-candidates")
    async def list_context_candidates(
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        return await _aggregate_runtime_lists(
            request,
            context,
            lambda adapter: adapter.list_context_candidates(context),
            _rewrite_context_candidate,
        )

    @gateway.post("/v1/context-candidates/{candidate_id}/{action}")
    async def review_context_candidate(
        candidate_id: str,
        action: str,
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        if action not in {"approve", "reject"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported context review action.")
        name, native_id, spec = _resolve_resource(request, candidate_id, "context_candidate")
        body = await request.body() or b"{}"
        if len(body) > 24_000:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Context review is too large.")
        upstream = await _adapter_call(
            create_adapter(spec).review_context_candidate(context, native_id, action, body)
        )
        return _rewrite_json_response(
            upstream,
            lambda payload: _rewrite_context_review_response(payload, name),
        )

    return gateway


async def _create_run_for_payload(
    request: Request,
    context: RuntimeContext,
    source_payload: dict[str, Any],
) -> JSONResponse:
    payload = dict(source_payload)
    workflow = payload.get("workflow")
    supported_workflows = {
        "progressive-hint",
        "error-diagnosis",
        "training-plan",
        "learning-profile",
    }
    if workflow is not None and workflow not in supported_workflows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported Agent workflow.")
    if workflow is not None and not isinstance(payload.get("input"), str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow input must be a string.")
    public_session_id = payload.get("session_id")
    degraded_from: str | None = None
    if public_session_id is None:
        name, spec = _registry(request).active_runtime()
    elif isinstance(public_session_id, str):
        name, native_session_id, spec = _resolve_resource(request, public_session_id, "session")
        payload["session_id"] = native_session_id
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id must be a string.")
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    reservation = _reserve_run(request, context, name)
    try:
        if public_session_id is None:
            try:
                upstream = await _adapter_call(create_adapter(spec).create_run(context, body))
            except HTTPException as first_error:
                if not request.app.state.gateway_settings.auto_failover:
                    raise
                fallback = await _healthy_fallback(request, excluded={name})
                if fallback is None:
                    raise first_error
                fallback_name, fallback_spec = fallback
                _ledger(request).release(reservation)
                reservation = _reserve_run(request, context, fallback_name)
                name, spec, degraded_from = fallback_name, fallback_spec, name
                upstream = await _adapter_call(create_adapter(spec).create_run(context, body))
            else:
                if upstream.status_code >= 500 and request.app.state.gateway_settings.auto_failover:
                    fallback = await _healthy_fallback(request, excluded={name})
                    if fallback is not None:
                        fallback_name, fallback_spec = fallback
                        _ledger(request).release(reservation)
                        reservation = _reserve_run(request, context, fallback_name)
                        name, spec, degraded_from = fallback_name, fallback_spec, name
                        upstream = await _adapter_call(create_adapter(spec).create_run(context, body))
        else:
            upstream = await _adapter_call(create_adapter(spec).create_run(context, body))
        if not 200 <= upstream.status_code < 300:
            _ledger(request).release(reservation)
            return _rewrite_json_response(upstream, lambda value: _rewrite_named_ids(value, name))
        native_payload = _json_object(upstream)
        native_run_id = native_payload.get("run_id")
        if not isinstance(native_run_id, str):
            raise RuntimeAdapterError("Runtime returned a run without an ID.")
        public_run_id = encode_public_id("run", name, native_run_id)
        public_session = None
        native_response_session = native_payload.get("session_id")
        if isinstance(native_response_session, str):
            public_session = encode_public_id("session", name, native_response_session)
        elif isinstance(public_session_id, str):
            public_session = public_session_id
        rewritten = _with_failover_metadata(
            _rewrite_named_ids(native_payload, name),
            runtime_name=name,
            degraded_from=degraded_from,
        )
        _ledger(request).commit_run(
            reservation,
            public_id=public_run_id,
            native_id=native_run_id,
            session_public_id=public_session,
            workflow=workflow if isinstance(workflow, str) else None,
            status=str(native_payload.get("status") or "accepted"),
            request_payload={**payload, "session_id": public_session},
            response_payload=rewritten if isinstance(rewritten, dict) else {},
        )
        return JSONResponse(rewritten, status_code=upstream.status_code)
    except BaseException:
        _ledger(request).release(reservation)
        raise


async def _refresh_scheduled_profile_run(
    request: Request,
    user_id: str,
    source_watermark: str,
) -> None:
    refresh = _ledger(request).get_profile_refresh(user_id)
    if (
        refresh is None
        or refresh.get("source_watermark") == source_watermark
        or refresh.get("state") != "scheduled"
        or not isinstance(refresh.get("run_public_id"), str)
    ):
        return
    run_id = refresh["run_public_id"]
    try:
        stored = _ledger(request).get_run(run_id, user_id)
    except (KeyError, LedgerOwnershipError):
        return
    if stored is None or stored.get("status") in {"completed", "failed", "cancelled", "interrupted"}:
        return
    try:
        _name, native_id, spec = _resolve_resource(request, run_id, "run")
        upstream = await create_adapter(spec).get_run(
            RuntimeContext(user_id=user_id, session_key=f"syncode-learning-profile-{user_id}"),
            native_id,
        )
        if not 200 <= upstream.status_code < 300:
            return
        payload = _rewrite_named_ids(_json_object(upstream), _name)
        if isinstance(payload, dict):
            _ledger(request).update_run(run_id, user_id, payload)
    except (HTTPException, RuntimeAdapterError, RuntimeNotFoundError, PublicIdError, ValueError):
        return


def _required_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RegistryError(f"Missing required setting: {name}")
    if "\n" in value or "\r" in value:
        raise RegistryError(f"Invalid newline in setting: {name}")
    return value


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RegistryError(f"Invalid integer setting: {name}") from exc
    if value < minimum:
        raise RegistryError(f"{name} must be at least {minimum}.")
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise RegistryError(f"Invalid boolean setting: {name}")


def _registry(request: Request) -> RuntimeRegistry:
    return request.app.state.runtime_registry


def _ledger(request: Request) -> RuntimeLedger:
    return request.app.state.runtime_ledger


def _reserve_run(request: Request, context: RuntimeContext, runtime_name: str):
    try:
        return _ledger(request).reserve(context.user_id, runtime_name)
    except AdmissionLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "run_concurrency_limit",
                "message": str(exc),
                "scope": exc.scope,
                "limit": exc.limit,
            },
            headers={"Retry-After": "5"},
        ) from exc


async def _healthy_fallback(
    request: Request,
    *,
    excluded: set[str],
) -> tuple[str, RuntimeSpec] | None:
    snapshot = _registry(request).snapshot()
    for name, spec in snapshot.runtimes.items():
        if name in excluded:
            continue
        try:
            if await create_adapter(spec).health():
                return name, spec
        except (RuntimeAdapterError, RegistryError, ValueError):
            continue
    return None


async def _call_new_resource_with_failover(
    request: Request,
    call: Any,
) -> tuple[str, RuntimeResponse, str | None]:
    active_name, active_spec = _registry(request).active_runtime()
    try:
        response = await call(active_spec)
        if response.status_code < 500:
            return active_name, response, None
    except RuntimeAdapterError as first_error:
        response = None
        failure = first_error
    else:
        failure = RuntimeAdapterError(f"Runtime returned HTTP {response.status_code}.")
    if not request.app.state.gateway_settings.auto_failover:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(failure))
    fallback = await _healthy_fallback(request, excluded={active_name})
    if fallback is None:
        if response is not None:
            return active_name, response, None
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(failure))
    name, spec = fallback
    try:
        return name, await call(spec), active_name
    except RuntimeAdapterError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


def _with_failover_metadata(payload: Any, *, runtime_name: str, degraded_from: str | None) -> Any:
    if not isinstance(payload, dict):
        return payload
    result = dict(payload)
    result["runtime"] = runtime_name
    if degraded_from:
        result["degraded_from"] = degraded_from
    return result


def _authorize(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    expected = request.app.state.gateway_settings.gateway_key
    supplied = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else ""
    if not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway credential.")


def _runtime_context(
    request: Request,
    authorization: str | None = Header(default=None),
    user_id: str | None = Header(default=None, alias="X-SynCode-User-ID"),
    session_key: str | None = Header(default=None, alias="X-SynCode-Session-Key"),
) -> RuntimeContext:
    _authorize(request, authorization)
    if not user_id or not user_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Runtime user identity.")
    if not session_key or len(session_key) > 128 or any(ord(char) < 33 or ord(char) > 126 for char in session_key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Runtime session key.")
    return RuntimeContext(user_id=user_id, session_key=session_key)


def _resolve_resource(request: Request, public_id: str, kind: str) -> tuple[str, str, RuntimeSpec]:
    try:
        name, native_id = decode_public_id(public_id, kind)
        spec = _registry(request).runtime(name)
        return name, native_id, spec
    except PublicIdError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="The owning Runtime is no longer registered.") from exc


async def _adapter_call(awaitable: Any) -> RuntimeResponse:
    try:
        return await awaitable
    except RuntimeAdapterError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


def _json_object(upstream: RuntimeResponse) -> dict[str, Any]:
    try:
        payload = json.loads(upstream.content)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeAdapterError("Runtime returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise RuntimeAdapterError("Runtime returned an invalid response object.")
    return payload


def _rewrite_json_response(upstream: RuntimeResponse, rewrite: Any) -> Response:
    try:
        payload = rewrite(json.loads(upstream.content))
    except (json.JSONDecodeError, UnicodeDecodeError, PublicIdError, TypeError, ValueError):
        if 200 <= upstream.status_code < 300:
            return JSONResponse({"message": "Agent Runtime returned an invalid response."}, status_code=502)
        return Response(upstream.content, status_code=upstream.status_code, media_type=upstream.content_type)
    return JSONResponse(payload, status_code=upstream.status_code)


def _rewrite_session_response(payload: Any, runtime_name: str) -> Any:
    value = _rewrite_named_ids(payload, runtime_name)
    if isinstance(value, dict) and isinstance(value.get("session"), dict):
        session = value["session"]
        if isinstance(session.get("id"), str):
            session["id"] = encode_public_id("session", runtime_name, session["id"])
            session["runtime"] = runtime_name
    elif isinstance(value, dict) and isinstance(value.get("id"), str):
        value["id"] = encode_public_id("session", runtime_name, value["id"])
        value["runtime"] = runtime_name
    return value


def _rewrite_named_ids(value: Any, runtime_name: str) -> Any:
    if isinstance(value, list):
        return [_rewrite_named_ids(item, runtime_name) for item in value]
    if not isinstance(value, dict):
        return value
    result: dict[str, Any] = {}
    for key, item in value.items():
        if key == "run_id" and isinstance(item, str):
            result[key] = encode_public_id("run", runtime_name, item)
        elif key == "session_id" and isinstance(item, str):
            result[key] = encode_public_id("session", runtime_name, item)
        elif key == "context_candidate_id" and isinstance(item, str):
            result[key] = encode_public_id("context_candidate", runtime_name, item)
        else:
            result[key] = _rewrite_named_ids(item, runtime_name)
    return result


def _rewrite_memory_document(item: dict[str, Any], runtime_name: str, active: bool) -> dict[str, Any]:
    return {**item, "runtime": runtime_name, "active": active}


def _rewrite_memory_candidate(item: dict[str, Any], runtime_name: str, active: bool) -> dict[str, Any]:
    native_id = item.get("id")
    if not isinstance(native_id, str):
        raise ValueError("Memory candidate has no ID.")
    return {
        **item,
        "id": encode_public_id("memory_candidate", runtime_name, native_id),
        "runtime": runtime_name,
        "active": active,
    }


def _rewrite_memory_review_response(payload: Any, runtime_name: str) -> Any:
    if not isinstance(payload, dict):
        return payload
    result = dict(payload)
    candidate_id = result.get("candidate_id")
    if isinstance(candidate_id, str):
        result["candidate_id"] = encode_public_id("memory_candidate", runtime_name, candidate_id)
    result["runtime"] = runtime_name
    return result


def _rewrite_context_candidate(item: dict[str, Any], runtime_name: str, active: bool) -> dict[str, Any]:
    native_id = item.get("id")
    if not isinstance(native_id, str):
        raise ValueError("Context candidate has no ID.")
    result = dict(item)
    result["id"] = encode_public_id("context_candidate", runtime_name, native_id)
    result["runtime"] = runtime_name
    result["active"] = active
    if isinstance(result.get("run_id"), str):
        result["run_id"] = encode_public_id("run", runtime_name, result["run_id"])
    if isinstance(result.get("session_id"), str):
        result["session_id"] = encode_public_id("session", runtime_name, result["session_id"])
    return result


def _rewrite_context_review_response(payload: Any, runtime_name: str) -> Any:
    if not isinstance(payload, dict):
        return payload
    result = dict(payload)
    candidate_id = result.get("candidate_id")
    if isinstance(candidate_id, str):
        result["candidate_id"] = encode_public_id("context_candidate", runtime_name, candidate_id)
    result["runtime"] = runtime_name
    return result


async def _aggregate_runtime_lists(
    request: Request,
    context: RuntimeContext,
    load: Any,
    rewrite_item: Any,
) -> Response:
    snapshot = _registry(request).snapshot()

    async def load_one(name: str, spec: RuntimeSpec) -> tuple[str, RuntimeResponse | None, str | None]:
        try:
            response = await load(create_adapter(spec))
            if not 200 <= response.status_code < 300:
                raise RuntimeAdapterError(f"Runtime returned HTTP {response.status_code}.")
            return name, response, None
        except (RuntimeAdapterError, RegistryError, ValueError) as exc:
            return name, None, str(exc)

    results = await asyncio.gather(*(load_one(name, spec) for name, spec in snapshot.runtimes.items()))
    rows: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    for name, upstream, error in results:
        if error is not None or upstream is None:
            if name == snapshot.active:
                return JSONResponse(
                    {"message": "The active Agent Runtime is unavailable."},
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            warnings.append({"runtime": name, "message": error or "Runtime is unavailable."})
            continue
        try:
            payload = _json_object(upstream)
            data = payload.get("data", [])
            if not isinstance(data, list):
                raise RuntimeAdapterError("Runtime returned an invalid resource list.")
            for item in data:
                if isinstance(item, dict):
                    rows.append(rewrite_item(item, name, name == snapshot.active))
        except (RuntimeAdapterError, PublicIdError, ValueError) as exc:
            if name == snapshot.active:
                return JSONResponse(
                    {"message": "The active Agent Runtime returned invalid data."},
                    status_code=status.HTTP_502_BAD_GATEWAY,
                )
            warnings.append({"runtime": name, "message": str(exc)})
    return JSONResponse({"data": rows, "total": len(rows), "warnings": warnings})


def _rewrite_sse_frame(lines: list[str], runtime_name: str) -> str:
    data_indexes = [index for index, line in enumerate(lines) if line.startswith("data:")]
    if not data_indexes:
        return "\n".join(lines)
    raw = "\n".join(lines[index][5:].lstrip() for index in data_indexes)
    try:
        payload = _rewrite_named_ids(json.loads(raw), runtime_name)
    except (json.JSONDecodeError, PublicIdError, TypeError, ValueError):
        return "\n".join(lines)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    first = data_indexes[0]
    data_index_set = set(data_indexes)
    rewritten: list[str] = []
    for index, line in enumerate(lines):
        if index == first:
            rewritten.append(f"data: {encoded}")
        elif index not in data_index_set:
            rewritten.append(line)
    return "\n".join(rewritten)


def _persist_sse_frame(
    request: Request,
    context: RuntimeContext,
    run_id: str,
    frame: str,
) -> None:
    event_name = "message"
    event_id: str | None = None
    data: list[str] = []
    for line in frame.replace("\r", "").split("\n"):
        if line.startswith("id:"):
            candidate = line[3:].strip()
            event_id = candidate or None
        elif line.startswith("event:"):
            event_name = line[6:].strip() or "message"
        elif line.startswith("data:"):
            data.append(line[5:].lstrip())
    if not data:
        return
    try:
        payload = json.loads("\n".join(data))
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    if event_name == "message" and isinstance(payload.get("event"), str):
        event_name = payload["event"]
    try:
        _ledger(request).append_event(
            run_id,
            context.user_id,
            upstream_event_id=event_id,
            event_name=event_name,
            payload=payload,
            frame=frame,
        )
    except (KeyError, LedgerOwnershipError, sqlite3.Error):
        # Legacy runs created before the durable ledger remain streamable.
        return


def _session_sort_key(item: dict[str, Any]) -> float:
    value = item.get("last_active") or item.get("started_at")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0


app = create_app()
