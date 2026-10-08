from __future__ import annotations

from dataclasses import dataclass
import hmac
import os
import re

from fastmcp.server.dependencies import get_http_headers


PROFILE_PATTERN = re.compile(r"^syncode-u(?P<user_id>[0-9]+)$")


class ToolIdentityError(PermissionError):
    pass


@dataclass(frozen=True)
class ToolIdentity:
    profile: str
    user_id: str


def user_id_from_profile(profile: str) -> str:
    match = PROFILE_PATTERN.fullmatch(profile.strip())
    if match is None:
        raise ToolIdentityError("Hermes profile identity is invalid.")
    return match.group("user_id")


def resolve_tool_identity() -> ToolIdentity:
    headers = get_http_headers(include_all=True)
    expected_key = (os.getenv("SYNCODE_MCP_SERVICE_KEY") or "").strip()
    if not expected_key:
        raise ToolIdentityError("MCP service authentication is not configured.")
    authorization = headers.get("authorization", "")
    supplied_key = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    if not supplied_key or not hmac.compare_digest(supplied_key, expected_key):
        raise ToolIdentityError("MCP service authentication failed.")

    profile = headers.get("x-syncode-hermes-profile", "").strip()
    return ToolIdentity(profile=profile, user_id=user_id_from_profile(profile))
