from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import hmac
import json
import os
from pathlib import Path
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
        yield

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
        name, spec = _registry(request).active_runtime()
        upstream = await _adapter_call(create_adapter(spec).create_session(context, await request.body()))
        return _rewrite_json_response(upstream, lambda payload: _rewrite_session_response(payload, name))

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
        workflow = payload.get("workflow")
        if workflow is not None and workflow not in {"progressive-hint", "error-diagnosis", "training-plan"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported Agent workflow.")
        if workflow is not None and not isinstance(payload.get("input"), str):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow input must be a string.")
        public_session_id = payload.get("session_id")
        if public_session_id is None:
            name, spec = _registry(request).active_runtime()
        elif isinstance(public_session_id, str):
            name, native_session_id, spec = _resolve_resource(request, public_session_id, "session")
            payload["session_id"] = native_session_id
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id must be a string.")
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        upstream = await _adapter_call(create_adapter(spec).create_run(context, body))
        return _rewrite_json_response(upstream, lambda value: _rewrite_named_ids(value, name))

    @gateway.get("/v1/runs/{run_id}/events")
    async def run_events(
        run_id: str,
        request: Request,
        context: RuntimeContext = Depends(_runtime_context),
    ) -> Response:
        name, native_id, spec = _resolve_resource(request, run_id, "run")
        try:
            upstream = await create_adapter(spec).run_events(context, native_id)
        except RuntimeAdapterError as exc:
            return JSONResponse({"message": str(exc)}, status_code=status.HTTP_502_BAD_GATEWAY)
        if not 200 <= upstream.status_code < 300:
            content = await upstream.bytes()
            content_type = upstream.content_type
            status_code = upstream.status_code
            await upstream.close()
            return Response(content, status_code=status_code, media_type=content_type)

        async def stream() -> AsyncIterator[bytes]:
            frame: list[str] = []
            try:
                async for line in upstream.lines():
                    if line == "":
                        yield (_rewrite_sse_frame(frame, name) + "\n\n").encode("utf-8")
                        frame = []
                    else:
                        frame.append(line)
                if frame:
                    yield (_rewrite_sse_frame(frame, name) + "\n\n").encode("utf-8")
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
        upstream = await _adapter_call(
            create_adapter(spec).control_run(context, native_id, action, await request.body() or b"{}")
        )
        return _rewrite_json_response(upstream, lambda payload: _rewrite_named_ids(payload, name))

    return gateway


def _required_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RegistryError(f"Missing required setting: {name}")
    if "\n" in value or "\r" in value:
        raise RegistryError(f"Invalid newline in setting: {name}")
    return value


def _registry(request: Request) -> RuntimeRegistry:
    return request.app.state.runtime_registry


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
    if not 200 <= upstream.status_code < 300:
        return Response(upstream.content, status_code=upstream.status_code, media_type=upstream.content_type)
    try:
        payload = rewrite(json.loads(upstream.content))
    except (json.JSONDecodeError, UnicodeDecodeError, PublicIdError, TypeError, ValueError):
        return JSONResponse({"message": "Agent Runtime returned an invalid response."}, status_code=502)
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
        else:
            result[key] = _rewrite_named_ids(item, runtime_name)
    return result


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
