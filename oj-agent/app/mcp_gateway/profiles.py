from __future__ import annotations

import os
import errno
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
        if self._is_complete(target):
            return False

        profiles_dir = target.parent
        profiles_dir.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{profile}-", dir=profiles_dir))
        try:
            config = {
                "model": {"provider": "deepseek", "default": os.getenv("HERMES_MODEL", "deepseek-chat")},
                "skills": {"external_dirs": [self.skills_dir]},
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
