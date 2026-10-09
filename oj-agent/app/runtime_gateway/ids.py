from __future__ import annotations

import base64
import re


RUNTIME_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
_PREFIXES = {
    "session": "rts",
    "run": "rtr",
    "memory_candidate": "rtm",
    "context_candidate": "rtc",
}


class PublicIdError(ValueError):
    pass


def validate_runtime_name(name: str) -> str:
    if not RUNTIME_NAME_RE.fullmatch(name):
        raise PublicIdError("Runtime name must match [a-z][a-z0-9-]{0,31}.")
    return name


def encode_public_id(kind: str, runtime_name: str, native_id: str) -> str:
    prefix = _prefix(kind)
    validate_runtime_name(runtime_name)
    if not native_id or len(native_id) > 4096 or "\x00" in native_id:
        raise PublicIdError(f"Invalid native {kind} ID.")
    encoded = base64.urlsafe_b64encode(native_id.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{prefix}.{runtime_name}.{encoded}"


def decode_public_id(value: str, kind: str) -> tuple[str, str]:
    prefix = _prefix(kind)
    if not value or len(value) > 8192:
        raise PublicIdError(f"Invalid public {kind} ID.")
    parts = value.split(".", 2)
    if len(parts) != 3 or parts[0] != prefix:
        raise PublicIdError(f"Invalid public {kind} ID.")
    runtime_name = validate_runtime_name(parts[1])
    encoded = parts[2]
    if not encoded or not re.fullmatch(r"[A-Za-z0-9_-]+", encoded):
        raise PublicIdError(f"Invalid public {kind} ID.")
    try:
        native = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise PublicIdError(f"Invalid public {kind} ID.") from exc
    if not native or len(native) > 4096 or "\x00" in native:
        raise PublicIdError(f"Invalid public {kind} ID.")
    return runtime_name, native


def _prefix(kind: str) -> str:
    try:
        return _PREFIXES[kind]
    except KeyError as exc:
        raise PublicIdError(f"Unsupported resource kind: {kind}") from exc
