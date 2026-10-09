from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, AsyncIterator, Callable
from urllib.parse import quote

import httpx

from app.runtime_gateway.registry import RuntimeSpec


HERMES_SKILL_BY_WORKFLOW = {
    "progressive-hint": "syncode-tutor",
    "error-diagnosis": "syncode-diagnosis",
    "training-plan": "syncode-training-plan",
}
_HERMES_SKILL_PREFIX = re.compile(r"^/syncode-(?:tutor|diagnosis|training-plan)\s*", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    user_id: str
    session_key: str


@dataclass(slots=True)
class RuntimeResponse:
    status_code: int
    content: bytes
    content_type: str


@dataclass(slots=True)
class RuntimeStream:
    status_code: int
    response: httpx.Response
    client: httpx.AsyncClient

    @property
    def content_type(self) -> str:
        return self.response.headers.get("content-type", "application/octet-stream")

    async def bytes(self) -> bytes:
        return await self.response.aread()

    async def close(self) -> None:
        await self.response.aclose()
        await self.client.aclose()

    async def lines(self) -> AsyncIterator[str]:
        async for line in self.response.aiter_lines():
            yield line


class RuntimeAdapterError(RuntimeError):
    pass


class RuntimeAdapter:
    async def health(self) -> bool:
        raise NotImplementedError

    async def list_sessions(self, context: RuntimeContext, limit: int) -> RuntimeResponse:
        raise NotImplementedError

    async def create_session(self, context: RuntimeContext, body: bytes) -> RuntimeResponse:
        raise NotImplementedError

    async def update_session(self, context: RuntimeContext, session_id: str, body: bytes) -> RuntimeResponse:
        raise NotImplementedError

    async def list_messages(self, context: RuntimeContext, session_id: str, query: str) -> RuntimeResponse:
        raise NotImplementedError

    async def create_run(self, context: RuntimeContext, body: bytes) -> RuntimeResponse:
        raise NotImplementedError

    async def run_events(self, context: RuntimeContext, run_id: str) -> RuntimeStream:
        raise NotImplementedError

    async def control_run(self, context: RuntimeContext, run_id: str, action: str, body: bytes) -> RuntimeResponse:
        raise NotImplementedError


class HermesRuntimeAdapter(RuntimeAdapter):
    def __init__(self, spec: RuntimeSpec) -> None:
        self.spec = spec

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.spec.base_url}/health")
            return 200 <= response.status_code < 300
        except httpx.HTTPError:
            return False

    async def list_sessions(self, context: RuntimeContext, limit: int) -> RuntimeResponse:
        await self._ensure_profile(context)
        return await self._request(context, "GET", "/api/sessions", params={"limit": str(limit), "offset": "0"})

    async def create_session(self, context: RuntimeContext, body: bytes) -> RuntimeResponse:
        await self._ensure_profile(context)
        return await self._request(context, "POST", "/api/sessions", content=body)

    async def update_session(self, context: RuntimeContext, session_id: str, body: bytes) -> RuntimeResponse:
        return await self._request(context, "PATCH", f"/api/sessions/{quote(session_id, safe='')}", content=body)

    async def list_messages(self, context: RuntimeContext, session_id: str, query: str) -> RuntimeResponse:
        path = f"/api/sessions/{quote(session_id, safe='')}/messages"
        if query:
            path += f"?{query}"
        response = await self._request(context, "GET", path)
        if not 200 <= response.status_code < 300:
            return response
        try:
            payload = json.loads(response.content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return response
        translated = translate_hermes_messages(payload)
        return RuntimeResponse(
            status_code=response.status_code,
            content=json.dumps(translated, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            content_type="application/json",
        )

    async def create_run(self, context: RuntimeContext, body: bytes) -> RuntimeResponse:
        await self._ensure_profile(context)
        return await self._request(context, "POST", "/v1/runs", content=translate_hermes_run_body(body))

    async def run_events(self, context: RuntimeContext, run_id: str) -> RuntimeStream:
        client = httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0))
        request = client.build_request(
            "GET",
            self._profile_url(context, f"/v1/runs/{quote(run_id, safe='')}/events"),
            headers=self._headers(context),
        )
        try:
            response = await client.send(request, stream=True)
        except httpx.HTTPError as exc:
            await client.aclose()
            raise RuntimeAdapterError("Agent Runtime is unavailable.") from exc
        return RuntimeStream(status_code=response.status_code, response=response, client=client)

    async def control_run(self, context: RuntimeContext, run_id: str, action: str, body: bytes) -> RuntimeResponse:
        return await self._request(
            context,
            "POST",
            f"/v1/runs/{quote(run_id, safe='')}/{action}",
            content=body,
        )

    async def _ensure_profile(self, context: RuntimeContext) -> None:
        if not self.spec.provision_url:
            return
        profile = self._profile(context)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.spec.provision_url,
                    headers={"Authorization": f"Bearer {self.spec.provision_key}"},
                    json={"user_id": context.user_id, "profile": profile},
                )
        except httpx.HTTPError as exc:
            raise RuntimeAdapterError("Runtime user environment could not be initialized.") from exc
        if not 200 <= response.status_code < 300:
            raise RuntimeAdapterError("Runtime user environment could not be initialized.")

    async def _request(
        self,
        context: RuntimeContext,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        content: bytes | None = None,
    ) -> RuntimeResponse:
        headers = self._headers(context)
        if content is not None:
            headers["Content-Type"] = "application/json"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method,
                    self._profile_url(context, path),
                    headers=headers,
                    params=params,
                    content=content,
                )
        except httpx.HTTPError as exc:
            raise RuntimeAdapterError("Agent Runtime is unavailable.") from exc
        return RuntimeResponse(
            status_code=response.status_code,
            content=response.content,
            content_type=response.headers.get("content-type", "application/json"),
        )

    def _profile_url(self, context: RuntimeContext, path: str) -> str:
        if not path.startswith("/"):
            raise RuntimeAdapterError("Invalid Runtime adapter path.")
        return f"{self.spec.base_url}/p/{self._profile(context)}{path}"

    def _headers(self, context: RuntimeContext) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.spec.api_key}",
            "X-Hermes-Session-Key": context.session_key,
        }

    @staticmethod
    def _profile(context: RuntimeContext) -> str:
        if not context.user_id.isdigit():
            raise RuntimeAdapterError("Invalid Runtime user identity.")
        return f"syncode-u{context.user_id}"


class SynCodeV1RuntimeAdapter(RuntimeAdapter):
    """Adapter for Runtimes that implement the stable SynCode v1 protocol natively."""

    def __init__(self, spec: RuntimeSpec) -> None:
        self.spec = spec

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.spec.base_url}/health")
            return 200 <= response.status_code < 300
        except httpx.HTTPError:
            return False

    async def list_sessions(self, context: RuntimeContext, limit: int) -> RuntimeResponse:
        return await self._request(context, "GET", "/v1/sessions", params={"limit": str(limit), "offset": "0"})

    async def create_session(self, context: RuntimeContext, body: bytes) -> RuntimeResponse:
        return await self._request(context, "POST", "/v1/sessions", content=body)

    async def update_session(self, context: RuntimeContext, session_id: str, body: bytes) -> RuntimeResponse:
        return await self._request(context, "PATCH", f"/v1/sessions/{quote(session_id, safe='')}", content=body)

    async def list_messages(self, context: RuntimeContext, session_id: str, query: str) -> RuntimeResponse:
        path = f"/v1/sessions/{quote(session_id, safe='')}/messages"
        if query:
            path += f"?{query}"
        return await self._request(context, "GET", path)

    async def create_run(self, context: RuntimeContext, body: bytes) -> RuntimeResponse:
        return await self._request(context, "POST", "/v1/runs", content=body)

    async def run_events(self, context: RuntimeContext, run_id: str) -> RuntimeStream:
        client = httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0))
        request = client.build_request(
            "GET",
            f"{self.spec.base_url}/v1/runs/{quote(run_id, safe='')}/events",
            headers=self._headers(context),
        )
        try:
            response = await client.send(request, stream=True)
        except httpx.HTTPError as exc:
            await client.aclose()
            raise RuntimeAdapterError("Agent Runtime is unavailable.") from exc
        return RuntimeStream(status_code=response.status_code, response=response, client=client)

    async def control_run(self, context: RuntimeContext, run_id: str, action: str, body: bytes) -> RuntimeResponse:
        return await self._request(
            context,
            "POST",
            f"/v1/runs/{quote(run_id, safe='')}/{action}",
            content=body,
        )

    async def _request(
        self,
        context: RuntimeContext,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        content: bytes | None = None,
    ) -> RuntimeResponse:
        headers = self._headers(context)
        if content is not None:
            headers["Content-Type"] = "application/json"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method,
                    f"{self.spec.base_url}{path}",
                    headers=headers,
                    params=params,
                    content=content,
                )
        except httpx.HTTPError as exc:
            raise RuntimeAdapterError("Agent Runtime is unavailable.") from exc
        return RuntimeResponse(
            status_code=response.status_code,
            content=response.content,
            content_type=response.headers.get("content-type", "application/json"),
        )

    def _headers(self, context: RuntimeContext) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.spec.api_key}",
            "X-SynCode-User-ID": context.user_id,
            "X-SynCode-Session-Key": context.session_key,
        }


_ADAPTERS: dict[str, Callable[[RuntimeSpec], RuntimeAdapter]] = {
    "hermes": HermesRuntimeAdapter,
    "syncode-v1": SynCodeV1RuntimeAdapter,
}


def create_adapter(spec: RuntimeSpec) -> RuntimeAdapter:
    try:
        factory = _ADAPTERS[spec.adapter]
    except KeyError as exc:
        raise RuntimeAdapterError(f"Unsupported Runtime adapter: {spec.adapter}") from exc
    return factory(spec)


def translate_hermes_run_body(body: bytes) -> bytes:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeAdapterError("Invalid Runtime run request.") from exc
    if not isinstance(payload, dict):
        raise RuntimeAdapterError("Invalid Runtime run request.")
    workflow = payload.pop("workflow", None)
    if workflow is not None:
        skill = HERMES_SKILL_BY_WORKFLOW.get(workflow)
        user_input = payload.get("input")
        if skill is None or not isinstance(user_input, str):
            raise RuntimeAdapterError("Unsupported Runtime workflow request.")
        payload["input"] = f"/{skill} {user_input}".rstrip()
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def translate_hermes_messages(payload: Any) -> Any:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return payload
    for message in payload["data"]:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = _HERMES_SKILL_PREFIX.sub("", content, count=1)
            continue
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            for field in ("text", "content"):
                if isinstance(part.get(field), str):
                    part[field] = _HERMES_SKILL_PREFIX.sub("", part[field], count=1)
                    break
            else:
                continue
            break
    return payload
