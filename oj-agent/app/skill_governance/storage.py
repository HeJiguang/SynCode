from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Iterable

import yaml

from app.mcp_gateway.identity import user_id_from_profile


SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
ALLOWED_PACKAGE_ROOTS = {"references", "templates", "scripts", "assets"}
MAX_SKILL_FILE_BYTES = 1_048_576
MAX_PACKAGE_BYTES = 4 * MAX_SKILL_FILE_BYTES


class SkillStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class SkillDocument:
    name: str
    display_name: str
    description: str
    category: str | None
    relative_path: str
    content: str
    package: dict[str, str]
    content_hash: str
    modified_at: datetime


def _package_hash(files: dict[str, str]) -> str:
    digest = sha256()
    for path, content in sorted(files.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _declared_version(content: str) -> tuple[int, int, int] | None:
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) != 3:
        return None
    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None
    match = SEMVER_RE.fullmatch(str(frontmatter.get("version") or "").strip()) if isinstance(frontmatter, dict) else None
    return tuple(int(value) for value in match.groups()) if match else None


def parse_skill_document(skill_md: Path, root: Path) -> SkillDocument:
    root = root.resolve()
    if skill_md.is_symlink():
        raise SkillStorageError("Symbolic links are not valid Skill packages.")
    try:
        resolved = skill_md.resolve(strict=True)
        relative = resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise SkillStorageError("Skill path escapes its assigned store.") from exc
    if relative.name != "SKILL.md" or any(part.startswith(".") for part in relative.parts):
        raise SkillStorageError("Skill package path is not active.")

    package_dir = resolved.parent
    files: dict[str, str] = {}
    total_bytes = 0
    for candidate in sorted(package_dir.rglob("*")):
        if not candidate.is_file() or candidate.is_symlink():
            continue
        package_relative = candidate.relative_to(package_dir)
        if package_relative.name != "SKILL.md" and package_relative.parts[0] not in ALLOWED_PACKAGE_ROOTS:
            continue
        size = candidate.stat().st_size
        if size > MAX_SKILL_FILE_BYTES:
            raise SkillStorageError(f"Skill file is too large: {package_relative}")
        total_bytes += size
        if total_bytes > MAX_PACKAGE_BYTES:
            raise SkillStorageError("Skill package exceeds the governance snapshot limit.")
        try:
            files[package_relative.as_posix()] = candidate.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise SkillStorageError(f"Skill file must be UTF-8 text: {package_relative}") from exc

    content = files.get("SKILL.md", "")
    if not content.strip():
        raise SkillStorageError("Skill package has an empty SKILL.md.")
    frontmatter: dict = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) == 3:
            parsed = yaml.safe_load(parts[1]) or {}
            if isinstance(parsed, dict):
                frontmatter = parsed
    name = str(frontmatter.get("name") or package_dir.name).strip()
    if not SKILL_NAME_RE.fullmatch(name):
        raise SkillStorageError(f"Invalid Skill name: {name}")
    description = str(frontmatter.get("description") or "").strip()[:1000]
    display_name = str(frontmatter.get("title") or name).strip()[:128]
    category = relative.parts[-3] if len(relative.parts) >= 3 else None
    return SkillDocument(
        name=name,
        display_name=display_name,
        description=description,
        category=category,
        relative_path=relative.parent.as_posix(),
        content=content,
        package=files,
        content_hash=_package_hash(files),
        modified_at=datetime.fromtimestamp(resolved.stat().st_mtime, tz=timezone.utc),
    )


class HermesSkillStore:
    """Reads native Hermes profile skills and publishes reviewed platform packages."""

    def __init__(self) -> None:
        self.hermes_home = Path(os.getenv("HERMES_HOME", "/var/lib/hermes")).resolve()
        self.platform_root = Path(
            os.getenv("SYNCODE_PLATFORM_SKILL_STORE", str(self.hermes_home / "platform-skills"))
        ).resolve()

    def profile_root(self, *, user_id: str, profile: str) -> Path:
        if not user_id.isdecimal() or user_id_from_profile(profile) != user_id:
            raise SkillStorageError("Profile does not belong to the requested user.")
        profiles_root = self.hermes_home / "profiles"
        target = profiles_root / profile
        if target.is_symlink():
            raise SkillStorageError("Hermes profile path must not be a symbolic link.")
        try:
            target.resolve().relative_to(profiles_root.resolve())
        except ValueError as exc:
            raise SkillStorageError("Hermes profile path escapes the profile store.") from exc
        return target

    def scan_personal(self, *, user_id: str, profile: str) -> tuple[list[SkillDocument], list[str]]:
        skills_root = self.profile_root(user_id=user_id, profile=profile) / "skills"
        if not skills_root.exists():
            return [], []
        documents: list[SkillDocument] = []
        errors: list[str] = []
        provenance_error_count = len(errors)
        excluded_names, excluded_roots = self._external_skill_sources(skills_root, errors)
        if len(errors) != provenance_error_count:
            return [], errors
        for skill_md in sorted(skills_root.rglob("SKILL.md")):
            relative_skill_md = skill_md.relative_to(skills_root)
            if any(part.startswith(".") for part in relative_skill_md.parts):
                continue
            try:
                document = parse_skill_document(skill_md, skills_root)
                relative_root = Path(document.relative_path)
                if document.name in excluded_names or any(
                    relative_root == root or root in relative_root.parents for root in excluded_roots
                ):
                    continue
                documents.append(document)
            except SkillStorageError as exc:
                errors.append(f"{relative_skill_md}: {exc}")
        return documents, errors

    @staticmethod
    def _external_skill_sources(
        skills_root: Path,
        errors: list[str],
    ) -> tuple[set[str], set[Path]]:
        """Return Hermes-managed sources that must not become personal experience."""
        names: set[str] = set()
        roots: set[Path] = set()

        manifest = skills_root / ".bundled_manifest"
        if manifest.is_file():
            try:
                for line in manifest.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                    name = line.split(":", 1)[0].strip()
                    if name:
                        names.add(name)
            except OSError as exc:
                errors.append(f".bundled_manifest: {exc}")

        lock_file = skills_root / ".hub" / "lock.json"
        if lock_file.is_file():
            try:
                lock = json.loads(lock_file.read_text(encoding="utf-8-sig", errors="replace"))
                installed = lock.get("installed") if isinstance(lock, dict) else None
                if not isinstance(installed, dict):
                    raise ValueError("installed must be an object")
                for installed_name, entry in installed.items():
                    names.add(str(installed_name))
                    if not isinstance(entry, dict):
                        continue
                    install_path = entry.get("install_path")
                    if not isinstance(install_path, str) or not install_path.strip():
                        continue
                    relative = Path(install_path)
                    if relative.is_absolute() or ".." in relative.parts:
                        continue
                    resolved = (skills_root / relative).resolve()
                    try:
                        resolved.relative_to(skills_root.resolve())
                    except ValueError:
                        continue
                    roots.add(relative)
                    skill_md = resolved / "SKILL.md"
                    if skill_md.is_file():
                        try:
                            names.add(parse_skill_document(skill_md, skills_root).name)
                        except SkillStorageError:
                            pass
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                errors.append(f".hub/lock.json: {exc}")

        usage_file = skills_root / ".usage.json"
        if usage_file.is_file():
            try:
                usage = json.loads(usage_file.read_text(encoding="utf-8-sig", errors="replace"))
                if not isinstance(usage, dict):
                    raise ValueError("usage ledger must be an object")
                names.update(
                    str(name)
                    for name, record in usage.items()
                    if isinstance(record, dict) and record.get("created_by") == "installed"
                )
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                errors.append(f".usage.json: {exc}")

        return names, roots

    def scan_all_profiles(self) -> Iterable[tuple[str, str, list[SkillDocument], list[str]]]:
        profiles_root = self.hermes_home / "profiles"
        if not profiles_root.is_dir():
            return []
        rows = []
        for profile_dir in sorted(profiles_root.iterdir()):
            if not profile_dir.is_dir() or profile_dir.is_symlink():
                continue
            try:
                user_id = user_id_from_profile(profile_dir.name)
                documents, errors = self.scan_personal(user_id=user_id, profile=profile_dir.name)
                rows.append((user_id, profile_dir.name, documents, errors))
            except (ValueError, SkillStorageError):
                continue
        return rows

    def archive_personal(self, *, user_id: str, profile: str, name: str) -> Path:
        if not SKILL_NAME_RE.fullmatch(name):
            raise SkillStorageError("Invalid Skill name.")
        profile_root = self.profile_root(user_id=user_id, profile=profile)
        skills_root = profile_root / "skills"
        documents, _ = self.scan_personal(user_id=user_id, profile=profile)
        matches = [item for item in documents if item.name == name]
        if len(matches) != 1:
            raise SkillStorageError("Personal Skill was not found or is ambiguous.")
        source = skills_root / matches[0].relative_path
        archive_root = skills_root / ".archive"
        archive_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = archive_root / f"{stamp}-{name}"
        source.rename(target)
        return target

    def restore_personal(self, *, user_id: str, profile: str, name: str) -> Path:
        if not SKILL_NAME_RE.fullmatch(name):
            raise SkillStorageError("Invalid Skill name.")
        profile_root = self.profile_root(user_id=user_id, profile=profile)
        skills_root = profile_root / "skills"
        archive_root = skills_root / ".archive"
        candidates = sorted(archive_root.glob(f"*-{name}"), reverse=True) if archive_root.is_dir() else []
        if not candidates:
            raise SkillStorageError("Archived personal Skill was not found.")
        target = skills_root / name
        if target.exists():
            raise SkillStorageError("An active Skill with this name already exists.")
        candidates[0].rename(target)
        return target

    def write_personal_package(
        self,
        *,
        user_id: str,
        profile: str,
        name: str,
        package: dict[str, str],
    ) -> Path:
        root = self.profile_root(user_id=user_id, profile=profile) / "skills"
        documents, _ = self.scan_personal(user_id=user_id, profile=profile)
        matches = [document for document in documents if document.name == name]
        if len(matches) != 1:
            raise SkillStorageError("Personal Skill was not found or is ambiguous.")
        return self._atomic_write_package(
            root=root,
            name=name,
            category=matches[0].category,
            package=package,
        )

    def publish_platform(
        self,
        *,
        name: str,
        category: str | None,
        package: dict[str, str],
    ) -> Path:
        matches = [item for item in self.scan_platform() if item.name == name]
        if len(matches) > 1:
            raise SkillStorageError("Platform Skill name is ambiguous.")
        previous = self.platform_root / matches[0].relative_path if matches else None
        published = self._atomic_write_package(
            root=self.platform_root,
            name=name,
            category=category,
            package=package,
        )
        if previous and previous != published and previous.exists():
            shutil.rmtree(previous)
        return published

    def remove_platform(self, *, name: str) -> None:
        matches = [item for item in self.scan_platform() if item.name == name]
        if len(matches) > 1:
            raise SkillStorageError("Platform Skill name is ambiguous.")
        if matches:
            shutil.rmtree(self.platform_root / matches[0].relative_path)

    def archive_platform(self, *, name: str) -> Path:
        if not SKILL_NAME_RE.fullmatch(name):
            raise SkillStorageError("Invalid platform Skill name.")
        matches = [item for item in self.scan_platform() if item.name == name]
        if len(matches) != 1:
            raise SkillStorageError("Platform Skill was not found or is ambiguous.")
        source = self.platform_root / matches[0].relative_path
        archive_root = self.platform_root / ".archive"
        archive_root.mkdir(parents=True, exist_ok=True)
        target = archive_root / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{name}"
        source.rename(target)
        return target

    def restore_platform_archive(self, *, archive: Path, relative_path: str) -> Path:
        try:
            archive.resolve(strict=True).relative_to((self.platform_root / ".archive").resolve())
        except (OSError, ValueError) as exc:
            raise SkillStorageError("Platform archive path is invalid.") from exc
        target = self.platform_root / relative_path
        try:
            target.resolve().relative_to(self.platform_root.resolve())
        except ValueError as exc:
            raise SkillStorageError("Platform restore path escapes its store.") from exc
        if target.exists():
            raise SkillStorageError("Platform restore target already exists.")
        target.parent.mkdir(parents=True, exist_ok=True)
        archive.rename(target)
        return target

    def scan_platform(self) -> list[SkillDocument]:
        if not self.platform_root.is_dir():
            return []
        documents = []
        for skill_md in sorted(self.platform_root.rglob("SKILL.md")):
            try:
                documents.append(parse_skill_document(skill_md, self.platform_root))
            except SkillStorageError:
                continue
        return documents

    def seed_platform_skills(self, source_root: Path) -> int:
        if not source_root.is_dir():
            return 0
        seeded = 0
        self.platform_root.mkdir(parents=True, exist_ok=True)
        existing_by_name = {document.name: document for document in self.scan_platform()}
        for skill_md in sorted(source_root.rglob("SKILL.md")):
            document = parse_skill_document(skill_md, source_root)
            existing = existing_by_name.get(document.name)
            if existing:
                source_version = _declared_version(document.content)
                target_version = _declared_version(existing.content)
                if source_version is None or target_version is None or source_version <= target_version:
                    continue
            self.publish_platform(
                name=document.name,
                category=document.category,
                package=document.package,
            )
            existing_by_name[document.name] = document
            seeded += 1
        return seeded

    @staticmethod
    def package_from_content(content: str) -> dict[str, str]:
        if len(content.encode("utf-8")) > MAX_SKILL_FILE_BYTES:
            raise SkillStorageError("SKILL.md exceeds the package size limit.")
        return {"SKILL.md": content}

    @staticmethod
    def _atomic_write_package(
        *,
        root: Path,
        name: str,
        category: str | None,
        package: dict[str, str],
    ) -> Path:
        if not SKILL_NAME_RE.fullmatch(name):
            raise SkillStorageError("Invalid Skill name.")
        if category and not SKILL_NAME_RE.fullmatch(category):
            raise SkillStorageError("Invalid Skill category.")
        if not package or "SKILL.md" not in package:
            raise SkillStorageError("A Skill package must contain SKILL.md.")
        root.mkdir(parents=True, exist_ok=True)
        target_parent = root / category if category else root
        target_parent.mkdir(parents=True, exist_ok=True)
        target = target_parent / name
        staging = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=target_parent))
        backup: Path | None = None
        try:
            total = 0
            for relative, content in sorted(package.items()):
                relative_path = Path(relative)
                if relative_path.is_absolute() or ".." in relative_path.parts:
                    raise SkillStorageError("Skill package contains an unsafe path.")
                if relative != "SKILL.md" and relative_path.parts[0] not in ALLOWED_PACKAGE_ROOTS:
                    raise SkillStorageError(f"Unsupported Skill package path: {relative}")
                encoded = content.encode("utf-8")
                total += len(encoded)
                if len(encoded) > MAX_SKILL_FILE_BYTES or total > MAX_PACKAGE_BYTES:
                    raise SkillStorageError("Skill package exceeds the size limit.")
                output = staging / relative_path
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(content, encoding="utf-8")
            parsed = parse_skill_document(staging / "SKILL.md", staging)
            if parsed.name != name:
                raise SkillStorageError("Published package name does not match its frontmatter.")
            if target.exists():
                backup = target_parent / f".{name}.backup"
                if backup.exists():
                    shutil.rmtree(backup)
                target.rename(backup)
            staging.rename(target)
            if backup and backup.exists():
                shutil.rmtree(backup)
            return target
        except Exception:
            if target.exists() and backup and backup.exists():
                shutil.rmtree(target)
                backup.rename(target)
            raise
        finally:
            if staging.exists():
                shutil.rmtree(staging)


def package_json(package: dict[str, str]) -> str:
    return json.dumps(package, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
