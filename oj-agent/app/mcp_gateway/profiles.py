from __future__ import annotations

import os
import errno
import fcntl
from pathlib import Path
import shutil
import tempfile

import yaml

from app.mcp_gateway.identity import user_id_from_profile


class ProfileProvisionError(RuntimeError):
    pass


class HermesProfileProvisioner:
    def __init__(self) -> None:
        self.hermes_home = Path(os.getenv("HERMES_HOME", "/var/lib/hermes")).resolve()
        self.skills_dir = os.getenv("SYNCODE_HERMES_SKILLS_DIR", "/opt/syncode/hermes/skills")
        self.mcp_url = os.getenv("SYNCODE_MCP_PUBLIC_URL", "http://oj-agent-tools:8016/mcp")

    def ensure(self, *, user_id: str, profile: str) -> bool:
        if user_id_from_profile(profile) != user_id or not user_id.isdecimal():
            raise ProfileProvisionError("Profile does not belong to the requested user.")
        api_key = self._required("HERMES_API_SERVER_KEY")
        model_key = self._required("DEEPSEEK_API_KEY")
        mcp_key = self._required("SYNCODE_MCP_SERVICE_KEY")
        target = self.hermes_home / "profiles" / profile
        if target.is_symlink():
            raise ProfileProvisionError("Hermes profile path must not be a symbolic link.")
        profiles_dir = target.parent
        profiles_dir.mkdir(parents=True, exist_ok=True)
        config = self._managed_config(mcp_key)
        lock_path = profiles_dir / f".{profile}.lock"
        with lock_path.open("a+") as lock_file:
            lock_path.chmod(0o600)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            if self._is_complete(target):
                self._reconcile_config(target / "config.yaml", config)
                return False
            return self._create_profile(target, config, api_key, model_key)

    def _managed_config(self, mcp_key: str) -> dict:
        return {
            "model": {"provider": "deepseek", "default": os.getenv("HERMES_MODEL", "deepseek-chat")},
            "context": {"engine": "syncode_reviewed"},
            "skills": {"external_dirs": [self.skills_dir]},
            "memory": {
                "memory_enabled": True,
                "user_profile_enabled": True,
                "write_approval": True,
            },
            "platform_toolsets": {"api_server": ["memory", "syncode"]},
            "mcp_servers": {
                "syncode": {
                    "url": self.mcp_url,
                    "headers": {"Authorization": f"Bearer {mcp_key}"},
                    "identity_header": {
                        "name": "X-SynCode-Hermes-Profile",
                        "value_from": "profile",
                    },
                    "trust": "untrusted",
                    "tools": {"resources": False, "prompts": False},
                }
            },
        }

    def _create_profile(self, target: Path, config: dict, api_key: str, model_key: str) -> bool:
        staging = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        try:
            config_file = staging / "config.yaml"
            config_file.write_text(
                yaml.safe_dump(config, allow_unicode=False, sort_keys=False),
                encoding="utf-8",
            )
            config_file.chmod(0o600)
            (staging / "SOUL.md").write_text(
                "# SynCode Agent\n\nYou are the user's persistent SynCode learning agent. "
                "Use installed skills and tools to complete learning tasks.\n",
                encoding="utf-8",
            )
            env_file = staging / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "API_SERVER_ENABLED=true",
                        f"API_SERVER_KEY={api_key}",
                        f"DEEPSEEK_API_KEY={model_key}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            env_file.chmod(0o600)
            try:
                staging.rename(target)
            except OSError as exc:
                if exc.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                    raise
                if not self._is_complete(target):
                    raise ProfileProvisionError("Hermes profile exists but is incomplete.")
                return False
            return True
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    @staticmethod
    def _reconcile_config(path: Path, managed: dict) -> None:
        try:
            config = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ProfileProvisionError("Hermes profile config could not be read.") from exc
        if not isinstance(config, dict):
            raise ProfileProvisionError("Hermes profile config must be a mapping.")
        changed = False
        for key, value in managed.items():
            if key == "memory" and isinstance(config.get(key), dict):
                for memory_key, memory_value in value.items():
                    if config[key].get(memory_key) != memory_value:
                        config[key][memory_key] = memory_value
                        changed = True
            elif config.get(key) != value:
                config[key] = value
                changed = True
        if not changed:
            path.chmod(0o600)
            return
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(yaml.safe_dump(config, allow_unicode=False, sort_keys=False))
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _is_complete(path: Path) -> bool:
        return path.is_dir() and all((path / name).is_file() for name in ("config.yaml", ".env", "SOUL.md"))

    @staticmethod
    def _required(name: str) -> str:
        value = (os.getenv(name) or "").strip()
        if not value:
            raise ProfileProvisionError(f"Missing required setting: {name}")
        if "\n" in value or "\r" in value:
            raise ProfileProvisionError(f"Invalid newline in setting: {name}")
        return value
