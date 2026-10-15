from __future__ import annotations

import os
import errno
from pathlib import Path
import shutil
import tempfile

import yaml

from app.mcp_gateway.identity import user_id_from_profile
from app.skill_governance.storage import HermesSkillStore


class ProfileProvisionError(RuntimeError):
    pass


class HermesProfileProvisioner:
    def __init__(self) -> None:
        self.hermes_home = Path(os.getenv("HERMES_HOME", "/var/lib/hermes")).resolve()
        self.bundled_skills_dir = Path(
            os.getenv("SYNCODE_HERMES_BUNDLED_SKILLS_DIR", "/opt/syncode/hermes/skills")
        ).resolve()
        self.memory_provider_dir = Path(
            os.getenv(
                "SYNCODE_HERMES_MEMORY_PROVIDER_DIR",
                "/opt/syncode/hermes/plugins/syncode-learning-memory",
            )
        ).resolve()
        self.platform_skills_dir = os.getenv(
            "SYNCODE_HERMES_PLATFORM_SKILLS_DIR",
            "/opt/platform-data/platform-skills",
        )
        self.mcp_url = os.getenv("SYNCODE_MCP_PUBLIC_URL", "http://oj-agent-tools:8016/mcp")
        self.memory_endpoint = os.getenv(
            "SYNCODE_LEARNING_MEMORY_URL",
            f"{self.mcp_url.removesuffix('/mcp').rstrip('/')}/internal/learning-memory/recall",
        )

    def ensure(self, *, user_id: str, profile: str) -> bool:
        if user_id_from_profile(profile) != user_id or not user_id.isdecimal():
            raise ProfileProvisionError("Profile does not belong to the requested user.")
        api_key = self._required("HERMES_API_SERVER_KEY")
        model_key = self._required("DEEPSEEK_API_KEY")
        mcp_key = self._required("SYNCODE_MCP_SERVICE_KEY")
        HermesSkillStore().seed_platform_skills(self.bundled_skills_dir)
        target = self.hermes_home / "profiles" / profile
        if target.is_symlink():
            raise ProfileProvisionError("Hermes profile path must not be a symbolic link.")
        if self._is_complete(target):
            self._install_memory_provider(target)
            self._reconcile_config(target / "config.yaml", mcp_key=mcp_key)
            return False

        profiles_dir = target.parent
        profiles_dir.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{profile}-", dir=profiles_dir))
        try:
            self._install_memory_provider(staging)
            config = self._profile_config(mcp_key=mcp_key)
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
                        f"SYNCODE_MCP_SERVICE_KEY={mcp_key}",
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

    def _profile_config(self, *, mcp_key: str) -> dict:
        return {
            "model": {"provider": "deepseek", "default": os.getenv("HERMES_MODEL", "deepseek-chat")},
            "skills": {"external_dirs": [self.platform_skills_dir]},
            "auxiliary": {"background_review": {"enabled": True}},
            "curator": {
                "enabled": True,
                "interval_hours": 24,
                "stale_after_days": 14,
                "archive_after_days": 30,
                "consolidate": True,
                "prune_builtins": False,
                "archive_ttl_days": 0,
            },
            "memory": {
                "provider": "syncode-learning-memory",
                "syncode-learning-memory": {
                    "endpoint": self.memory_endpoint,
                    "timeout_seconds": 4.0,
                },
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

    def _reconcile_config(self, config_file: Path, *, mcp_key: str) -> None:
        try:
            current = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ProfileProvisionError("Hermes profile config cannot be read.") from exc
        desired = self._profile_config(mcp_key=mcp_key)
        changed = False
        for key in ("skills", "auxiliary", "curator", "memory", "platform_toolsets", "mcp_servers"):
            if current.get(key) != desired[key]:
                current[key] = desired[key]
                changed = True
        if not changed:
            return
        temporary = config_file.with_suffix(".yaml.tmp")
        temporary.write_text(
            yaml.safe_dump(current, allow_unicode=False, sort_keys=False),
            encoding="utf-8",
        )
        temporary.chmod(0o600)
        temporary.replace(config_file)

    def _install_memory_provider(self, profile_dir: Path) -> None:
        required = ("__init__.py", "plugin.yaml")
        missing = [name for name in required if not (self.memory_provider_dir / name).is_file()]
        if missing:
            raise ProfileProvisionError(
                f"SynCode Hermes memory provider is incomplete: {', '.join(missing)}"
            )
        target = profile_dir / "plugins" / "syncode-learning-memory"
        if target.is_symlink():
            raise ProfileProvisionError("Hermes memory provider path must not be a symbolic link.")
        target.mkdir(parents=True, exist_ok=True)
        for name in required:
            destination = target / name
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    prefix=f".{name}-",
                    suffix=".tmp",
                    dir=target,
                    delete=False,
                ) as handle:
                    handle.write((self.memory_provider_dir / name).read_bytes())
                    temporary = Path(handle.name)
                temporary.chmod(0o644)
                temporary.replace(destination)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)

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
