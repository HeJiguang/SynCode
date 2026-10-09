from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any
from urllib.parse import urlsplit

from app.runtime_gateway.ids import validate_runtime_name


class RegistryError(RuntimeError):
    pass


class RuntimeConflictError(RegistryError):
    pass


class RuntimeNotFoundError(RegistryError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimeSpec:
    adapter: str
    base_url: str
    api_key: str
    provision_url: str | None = None
    provision_key: str | None = None

    def __post_init__(self) -> None:
        if self.adapter not in {"hermes", "syncode-v1"}:
            raise RegistryError(f"Unsupported Runtime adapter: {self.adapter}")
        object.__setattr__(self, "base_url", _validated_url(self.base_url, "base_url"))
        if not self.api_key or "\n" in self.api_key or "\r" in self.api_key:
            raise RegistryError("Runtime api_key is required and must be a single line.")
        if self.provision_url:
            object.__setattr__(self, "provision_url", _validated_url(self.provision_url, "provision_url"))
            if not self.provision_key:
                raise RegistryError("provision_key is required when provision_url is configured.")
        if self.provision_key and ("\n" in self.provision_key or "\r" in self.provision_key):
            raise RegistryError("Runtime provision_key must be a single line.")
        if self.adapter == "syncode-v1" and (self.provision_url or self.provision_key):
            raise RegistryError("syncode-v1 Runtimes must manage their own user initialization.")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RuntimeSpec":
        allowed = {"adapter", "base_url", "api_key", "provision_url", "provision_key"}
        if set(value) - allowed:
            raise RegistryError("Runtime registration contains unsupported fields.")
        try:
            return cls(**value)
        except TypeError as exc:
            raise RegistryError("Runtime registration is incomplete.") from exc

    def stored(self) -> dict[str, str | None]:
        return asdict(self)

    def public(self) -> dict[str, str | bool | None]:
        return {
            "adapter": self.adapter,
            "base_url": self.base_url,
            "api_key_configured": bool(self.api_key),
            "provision_url": self.provision_url,
            "provision_key_configured": bool(self.provision_key),
        }


@dataclass(frozen=True, slots=True)
class RegistrySnapshot:
    active: str
    runtimes: dict[str, RuntimeSpec]


class RuntimeRegistry:
    def __init__(self, path: Path, default_name: str, default_spec: RuntimeSpec | None) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._snapshot: RegistrySnapshot | None = None
        self._mtime_ns: int | None = None
        validate_runtime_name(default_name)
        with self._lock:
            if not self.path.exists():
                if default_spec is None:
                    raise RegistryError("A default Runtime is required to initialize an empty registry.")
                self._persist_locked(RegistrySnapshot(active=default_name, runtimes={default_name: default_spec}))
            self._load_locked()

    def snapshot(self) -> RegistrySnapshot:
        with self._lock:
            self._reload_if_changed_locked()
            if self._snapshot is None:
                raise RegistryError("Runtime registry is not initialized.")
            return RegistrySnapshot(active=self._snapshot.active, runtimes=dict(self._snapshot.runtimes))

    def runtime(self, name: str) -> RuntimeSpec:
        snapshot = self.snapshot()
        try:
            return snapshot.runtimes[name]
        except KeyError as exc:
            raise RuntimeNotFoundError(f"Runtime is not registered: {name}") from exc

    def active_runtime(self) -> tuple[str, RuntimeSpec]:
        snapshot = self.snapshot()
        return snapshot.active, snapshot.runtimes[snapshot.active]

    def register(self, name: str, spec: RuntimeSpec) -> bool:
        validate_runtime_name(name)
        with self._lock:
            self._reload_if_changed_locked()
            assert self._snapshot is not None
            existing = self._snapshot.runtimes.get(name)
            if existing is not None:
                if existing == spec:
                    return False
                raise RuntimeConflictError(
                    f"Runtime '{name}' is immutable; register the replacement under a new name."
                )
            runtimes = dict(self._snapshot.runtimes)
            runtimes[name] = spec
            self._persist_locked(RegistrySnapshot(active=self._snapshot.active, runtimes=runtimes))
            return True

    def activate(self, name: str) -> bool:
        validate_runtime_name(name)
        with self._lock:
            self._reload_if_changed_locked()
            assert self._snapshot is not None
            if name not in self._snapshot.runtimes:
                raise RuntimeNotFoundError(f"Runtime is not registered: {name}")
            if self._snapshot.active == name:
                return False
            self._persist_locked(RegistrySnapshot(active=name, runtimes=dict(self._snapshot.runtimes)))
            return True

    def _reload_if_changed_locked(self) -> None:
        try:
            mtime_ns = self.path.stat().st_mtime_ns
        except FileNotFoundError as exc:
            raise RegistryError("Runtime registry file disappeared.") from exc
        if self._snapshot is None or mtime_ns != self._mtime_ns:
            self._load_locked()

    def _load_locked(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("version") != 1:
                raise RegistryError("Unsupported Runtime registry version.")
            active = validate_runtime_name(payload["active"])
            raw_runtimes = payload["runtimes"]
            if not isinstance(raw_runtimes, dict) or not raw_runtimes:
                raise RegistryError("Runtime registry must contain at least one Runtime.")
            runtimes = {
                validate_runtime_name(name): RuntimeSpec.from_dict(raw_spec)
                for name, raw_spec in raw_runtimes.items()
            }
            if active not in runtimes:
                raise RegistryError("Active Runtime is not registered.")
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, RegistryError):
                raise
            raise RegistryError("Runtime registry is invalid.") from exc
        self._snapshot = RegistrySnapshot(active=active, runtimes=runtimes)
        self._mtime_ns = self.path.stat().st_mtime_ns

    def _persist_locked(self, snapshot: RegistrySnapshot) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "active": snapshot.active,
            "runtimes": {name: spec.stored() for name, spec in sorted(snapshot.runtimes.items())},
        }
        fd, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self._snapshot = snapshot
        self._mtime_ns = self.path.stat().st_mtime_ns


def _validated_url(value: str, field: str) -> str:
    raw = str(value).strip().rstrip("/")
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise RegistryError(f"Runtime {field} must be an HTTP(S) URL without credentials.")
    if parsed.query or parsed.fragment:
        raise RegistryError(f"Runtime {field} must not contain a query or fragment.")
    return raw
