"""SynCode governance routes backed by Hermes' native memory implementation."""

from __future__ import annotations

from functools import partial
import re
from typing import Any

from aiohttp import web

from tools.memory_tool import apply_memory_pending, load_on_disk_store
from tools.write_approval import MEMORY, discard_pending, get_pending, list_pending
from plugins.context_engine.syncode_reviewed import (
    get_context_candidate,
    list_context_candidates,
    review_context_candidate,
)


_PENDING_ID_RE = re.compile(r"^[0-9a-f]{8}$")


def _http_routes(adapter: Any) -> list[tuple[str, str, Any]]:
    return [
        ("GET", "/v1/memories", partial(_handle_memories, adapter)),
        ("GET", "/v1/memory-candidates", partial(_handle_memory_candidates, adapter)),
        (
            "POST",
            "/v1/memory-candidates/{candidate_id}/approve",
            partial(_handle_approve_memory_candidate, adapter),
        ),
        (
            "POST",
            "/v1/memory-candidates/{candidate_id}/reject",
            partial(_handle_reject_memory_candidate, adapter),
        ),
        ("GET", "/v1/context-candidates", partial(_handle_context_candidates, adapter)),
        (
            "POST",
            "/v1/context-candidates/{candidate_id}/approve",
            partial(_handle_approve_context_candidate, adapter),
        ),
        (
            "POST",
            "/v1/context-candidates/{candidate_id}/reject",
            partial(_handle_reject_context_candidate, adapter),
        ),
    ]


def _authorized(adapter: Any, request: web.Request) -> web.Response | None:
    return adapter._check_auth(request)


def _candidate_id(request: web.Request) -> str | None:
    value = (request.match_info.get("candidate_id") or "").strip()
    return value if _PENDING_ID_RE.fullmatch(value) else None


def _candidate(record: dict[str, Any]) -> dict[str, Any] | None:
    candidate_id = str(record.get("id") or "")
    payload = record.get("payload")
    if not _PENDING_ID_RE.fullmatch(candidate_id) or not isinstance(payload, dict):
        return None
    return {
        "id": candidate_id,
        "action": str(record.get("action") or payload.get("action") or ""),
        "summary": str(record.get("summary") or ""),
        "origin": str(record.get("origin") or "foreground"),
        "created_at": record.get("created_at"),
        "target": str(payload.get("target") or "memory"),
        "proposal": payload,
    }


async def _handle_memories(adapter: Any, request: web.Request) -> web.Response:
    if auth_error := _authorized(adapter, request):
        return auth_error
    store = load_on_disk_store()
    return web.json_response(
        {
            "object": "syncode.memory.snapshot",
            "data": [
                {
                    "target": "memory",
                    "label": "MEMORY.md",
                    "entries": list(store.memory_entries),
                    "limit_chars": store.memory_char_limit,
                },
                {
                    "target": "user",
                    "label": "USER.md",
                    "entries": list(store.user_entries),
                    "limit_chars": store.user_char_limit,
                },
            ],
        }
    )


async def _handle_memory_candidates(adapter: Any, request: web.Request) -> web.Response:
    if auth_error := _authorized(adapter, request):
        return auth_error
    candidates = [candidate for row in list_pending(MEMORY) if (candidate := _candidate(row)) is not None]
    return web.json_response({"object": "list", "data": candidates, "total": len(candidates)})


async def _handle_approve_memory_candidate(adapter: Any, request: web.Request) -> web.Response:
    if auth_error := _authorized(adapter, request):
        return auth_error
    candidate_id = _candidate_id(request)
    if candidate_id is None:
        return web.json_response({"message": "Invalid memory candidate ID."}, status=400)
    record = get_pending(MEMORY, candidate_id)
    if record is None or not isinstance(record.get("payload"), dict):
        return web.json_response({"message": "Memory candidate not found."}, status=404)
    result = apply_memory_pending(record["payload"], load_on_disk_store())
    if not result.get("success"):
        return web.json_response(
            {"candidate_id": candidate_id, "status": "failed", "result": result},
            status=409,
        )
    if not discard_pending(MEMORY, candidate_id):
        return web.json_response(
            {
                "candidate_id": candidate_id,
                "status": "applied_cleanup_failed",
                "message": "Memory was applied, but its pending record could not be removed.",
                "result": result,
            },
            status=500,
        )
    return web.json_response({"candidate_id": candidate_id, "status": "approved", "result": result})


async def _handle_reject_memory_candidate(adapter: Any, request: web.Request) -> web.Response:
    if auth_error := _authorized(adapter, request):
        return auth_error
    candidate_id = _candidate_id(request)
    if candidate_id is None:
        return web.json_response({"message": "Invalid memory candidate ID."}, status=400)
    if get_pending(MEMORY, candidate_id) is None:
        return web.json_response({"message": "Memory candidate not found."}, status=404)
    if not discard_pending(MEMORY, candidate_id):
        return web.json_response({"message": "Memory candidate could not be rejected."}, status=500)
    return web.json_response({"candidate_id": candidate_id, "status": "rejected"})


async def _handle_context_candidates(adapter: Any, request: web.Request) -> web.Response:
    if auth_error := _authorized(adapter, request):
        return auth_error
    candidates = list_context_candidates()
    return web.json_response({"object": "list", "data": candidates, "total": len(candidates)})


async def _handle_approve_context_candidate(adapter: Any, request: web.Request) -> web.Response:
    if auth_error := _authorized(adapter, request):
        return auth_error
    candidate_id = _candidate_id(request)
    if candidate_id is None:
        return web.json_response({"message": "Invalid context candidate ID."}, status=400)
    try:
        body = await request.json() if request.can_read_body else {}
    except (ValueError, TypeError):
        return web.json_response({"message": "Request body must be JSON."}, status=400)
    if not isinstance(body, dict):
        return web.json_response({"message": "Request body must be an object."}, status=400)
    edited_summary = body.get("summary")
    if edited_summary is not None and not isinstance(edited_summary, str):
        return web.json_response({"message": "Edited summary must be text."}, status=400)
    try:
        candidate = review_context_candidate(candidate_id, "approve", edited_summary)
    except KeyError:
        return web.json_response({"message": "Context candidate not found."}, status=404)
    except ValueError as exc:
        return web.json_response({"message": str(exc)}, status=409)
    return web.json_response({"candidate_id": candidate_id, "status": candidate["status"]})


async def _handle_reject_context_candidate(adapter: Any, request: web.Request) -> web.Response:
    if auth_error := _authorized(adapter, request):
        return auth_error
    candidate_id = _candidate_id(request)
    if candidate_id is None:
        return web.json_response({"message": "Invalid context candidate ID."}, status=400)
    if get_context_candidate(candidate_id) is None:
        return web.json_response({"message": "Context candidate not found."}, status=404)
    try:
        candidate = review_context_candidate(candidate_id, "reject")
    except ValueError as exc:
        return web.json_response({"message": str(exc)}, status=409)
    return web.json_response({"candidate_id": candidate_id, "status": candidate["status"]})
