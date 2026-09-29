from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
import shutil
import tarfile
from typing import Any
from urllib.parse import quote

import httpx

from app.domain.tool_permissions import ToolActionRequest, normalize_public_github_repository


class GitHubRepositoryError(RuntimeError):
    pass


def prepare_github_snapshot_request(
    request: ToolActionRequest,
    *,
    http_client: httpx.Client | None = None,
) -> tuple[ToolActionRequest, dict[str, Any]]:
    repository = normalize_public_github_repository(request.resource)
    if repository is None:
        raise GitHubRepositoryError("只允许访问格式合法的公开 GitHub 仓库。")
    owner, name = repository.removeprefix("https://github.com/").split("/", 1)
    client_context = nullcontext(http_client) if http_client is not None else httpx.Client(
        timeout=10.0,
        follow_redirects=False,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "syncode-agent"},
    )
    with client_context as client:
        metadata = _get_json(client, f"https://api.github.com/repos/{owner}/{name}")
        if metadata.get("private") is not False:
            raise GitHubRepositoryError("仓库不存在或不是公开仓库。")
        requested_sha = str(request.arguments.get("commit_sha") or "").strip().lower()
        revision = requested_sha or str(metadata.get("default_branch") or "").strip()
        if not revision:
            raise GitHubRepositoryError("GitHub 没有返回可验证的默认分支。")
        commit = _get_json(
            client,
            f"https://api.github.com/repos/{owner}/{name}/commits/{quote(revision, safe='')}",
        )
    commit_sha = str(commit.get("sha") or "").strip().lower()
    if len(commit_sha) != 40 or any(char not in "0123456789abcdef" for char in commit_sha):
        raise GitHubRepositoryError("GitHub 没有返回完整的 commit SHA。")
    if requested_sha and requested_sha != commit_sha:
        raise GitHubRepositoryError("GitHub 返回的 commit 与请求的固定 SHA 不一致。")
    prepared = request.model_copy(
        update={
            "resource": repository,
            "arguments": {**request.arguments, "commit_sha": commit_sha},
        }
    )
    return prepared, {
        "repository": repository,
        "commitSha": commit_sha,
        "defaultBranch": str(metadata.get("default_branch") or ""),
        "description": str(metadata.get("description") or "")[:500],
        "repositorySizeKb": int(metadata.get("size") or 0),
    }


def download_github_snapshot(
    request: ToolActionRequest,
    *,
    approval_id: str,
    data_dir: Path,
    constraints: dict[str, Any],
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    repository = normalize_public_github_repository(request.resource)
    commit_sha = str(request.arguments.get("commit_sha") or "").strip().lower()
    if repository is None or len(commit_sha) != 40 or any(char not in "0123456789abcdef" for char in commit_sha):
        raise GitHubRepositoryError("下载请求没有绑定公开仓库和完整 commit SHA。")

    max_download_bytes = int(constraints.get("maxDownloadBytes") or 100 * 1024 * 1024)
    max_extracted_bytes = int(constraints.get("maxExtractedBytes") or max_download_bytes * 2)
    max_files = int(constraints.get("maxFiles") or 5000)
    ttl_seconds = int(constraints.get("ttlSeconds") or 1800)
    snapshots_root = data_dir / "github-snapshots"
    snapshots_root.mkdir(parents=True, exist_ok=True)
    _prune_expired_snapshots(snapshots_root, ttl_seconds)

    snapshot_root = snapshots_root / approval_id
    if snapshot_root.exists():
        raise GitHubRepositoryError("该一次性审批已经创建过快照。")
    snapshot_root.mkdir(mode=0o700)
    archive_path = snapshot_root / "snapshot.tar.gz"
    extracted_root = snapshot_root / "files"
    extracted_root.mkdir(mode=0o700)

    owner, name = repository.removeprefix("https://github.com/").split("/", 1)
    url = f"https://codeload.github.com/{owner}/{name}/tar.gz/{commit_sha}"
    client_context = nullcontext(http_client) if http_client is not None else httpx.Client(
        timeout=httpx.Timeout(60.0, connect=10.0),
        follow_redirects=False,
        headers={"User-Agent": "syncode-agent"},
    )
    try:
        with client_context as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_download_bytes:
                    raise GitHubRepositoryError("GitHub 快照超过下载大小限制。")
                downloaded = 0
                with archive_path.open("xb") as handle:
                    for chunk in response.iter_bytes():
                        downloaded += len(chunk)
                        if downloaded > max_download_bytes:
                            raise GitHubRepositoryError("GitHub 快照超过下载大小限制。")
                        handle.write(chunk)

        files, extracted_bytes, sample = _extract_snapshot(
            archive_path,
            extracted_root,
            max_files=max_files,
            max_extracted_bytes=max_extracted_bytes,
        )
        archive_path.unlink(missing_ok=True)
    except (httpx.HTTPError, OSError, tarfile.TarError, ValueError) as exc:
        shutil.rmtree(snapshot_root, ignore_errors=True)
        if isinstance(exc, GitHubRepositoryError):
            raise
        raise GitHubRepositoryError(f"GitHub 快照下载失败：{exc}") from exc
    except GitHubRepositoryError:
        shutil.rmtree(snapshot_root, ignore_errors=True)
        raise

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    return {
        "snapshotId": approval_id,
        "repository": repository,
        "commitSha": commit_sha,
        "fileCount": files,
        "extractedBytes": extracted_bytes,
        "fileSample": sample,
        "allowExecution": False,
        "expiresAt": expires_at.isoformat(),
    }


def _get_json(client: httpx.Client, url: str) -> dict[str, Any]:
    try:
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GitHubRepositoryError(f"无法验证 GitHub 仓库：{exc}") from exc
    if not isinstance(payload, dict):
        raise GitHubRepositoryError("GitHub 返回了无效响应。")
    return payload


def _extract_snapshot(
    archive_path: Path,
    extracted_root: Path,
    *,
    max_files: int,
    max_extracted_bytes: int,
) -> tuple[int, int, list[str]]:
    member_count = 0
    file_count = 0
    extracted_bytes = 0
    sample: list[str] = []
    with tarfile.open(archive_path, mode="r|gz") as archive:
        for member in archive:
            member_count += 1
            if member_count > max_files + 1:
                raise GitHubRepositoryError("GitHub 快照的文件数量超过限制。")
            relative = _safe_member_path(member.name)
            if relative is None:
                continue
            if member.issym() or member.islnk() or member.isdev():
                raise GitHubRepositoryError("GitHub 快照包含不允许的链接或设备文件。")
            destination = extracted_root.joinpath(*relative.parts)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            file_count += 1
            extracted_bytes += int(member.size)
            if file_count > max_files or extracted_bytes > max_extracted_bytes:
                raise GitHubRepositoryError("GitHub 快照解压后超过资源限制。")
            if relative.name.casefold() == ".gitmodules":
                raise GitHubRepositoryError("GitHub 快照声明了子模块，已拒绝下载。")
            source = archive.extractfile(member)
            if source is None:
                raise GitHubRepositoryError("GitHub 快照包含无法读取的文件。")
            prefix = source.read(200)
            if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
                raise GitHubRepositoryError("GitHub 快照包含 Git LFS 指针，已拒绝下载。")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                handle.write(prefix)
                shutil.copyfileobj(source, handle, length=64 * 1024)
            if len(sample) < 50:
                sample.append(relative.as_posix())
    return file_count, extracted_bytes, sample


def _safe_member_path(name: str) -> PurePosixPath | None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise GitHubRepositoryError("GitHub 快照包含越界路径。")
    parts = [part for part in path.parts if part not in {"", "."}]
    if len(parts) <= 1:
        return None
    return PurePosixPath(*parts[1:])


def _prune_expired_snapshots(root: Path, ttl_seconds: int) -> None:
    threshold = datetime.now(timezone.utc).timestamp() - max(ttl_seconds, 1)
    for child in root.iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < threshold:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            continue
