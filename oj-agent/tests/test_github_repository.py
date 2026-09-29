import io
from pathlib import Path
import tarfile

import httpx
import pytest

from app.domain.tool_permissions import ToolActionRequest, evaluate_tool_request
from app.integrations.github_repository import (
    GitHubRepositoryError,
    download_github_snapshot,
    prepare_github_snapshot_request,
)


def test_prepare_snapshot_resolves_public_repository_to_exact_commit():
    sha = "a" * 40

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/openai/openai-python":
            return httpx.Response(200, json={"private": False, "default_branch": "main", "size": 123})
        if request.url.path == "/repos/openai/openai-python/commits/main":
            return httpx.Response(200, json={"sha": sha})
        raise AssertionError(request.url)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        prepared, metadata = prepare_github_snapshot_request(
            ToolActionRequest(
                tool_name="github.download_snapshot",
                action="download",
                resource="openai/openai-python",
            ),
            http_client=client,
        )

    assert prepared.arguments["commit_sha"] == sha
    assert metadata["commitSha"] == sha
    assert evaluate_tool_request(prepared).constraints["approvalScope"] == "once"


def test_download_snapshot_extracts_regular_files_without_execution(tmp_path: Path):
    sha = "b" * 40
    archive = _archive_bytes(
        {
            "repo-root/README.md": b"# Safe repository\n",
            "repo-root/src/main.py": b"print('not executed')\n",
        }
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=archive, headers={"content-length": str(len(archive))})

    request = ToolActionRequest(
        tool_name="github.download_snapshot",
        action="download",
        resource="https://github.com/example/project",
        arguments={"commit_sha": sha},
    )
    constraints = evaluate_tool_request(request).constraints
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = download_github_snapshot(
            request,
            approval_id="approval-safe",
            data_dir=tmp_path,
            constraints=constraints,
            http_client=client,
        )

    assert result["allowExecution"] is False
    assert result["fileCount"] == 2
    assert (tmp_path / "github-snapshots" / "approval-safe" / "files" / "README.md").is_file()
    assert not (tmp_path / "github-snapshots" / "approval-safe" / "snapshot.tar.gz").exists()


def test_download_snapshot_rejects_path_traversal(tmp_path: Path):
    sha = "c" * 40
    archive = _archive_bytes({"../outside.txt": b"blocked"})

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=archive)

    request = ToolActionRequest(
        tool_name="github.download_snapshot",
        action="download",
        resource="https://github.com/example/project",
        arguments={"commit_sha": sha},
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GitHubRepositoryError, match="越界路径"):
            download_github_snapshot(
                request,
                approval_id="approval-unsafe",
                data_dir=tmp_path,
                constraints=evaluate_tool_request(request).constraints,
                http_client=client,
            )

    assert not (tmp_path / "outside.txt").exists()
    assert not (tmp_path / "github-snapshots" / "approval-unsafe").exists()


@pytest.mark.parametrize(
    ("file_name", "content", "message"),
    [
        ("repo-root/.GitModules", b"[submodule 'vendor']\n", "子模块"),
        (
            "repo-root/model.bin",
            b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\n",
            "Git LFS",
        ),
    ],
)
def test_download_snapshot_rejects_submodules_and_lfs_pointers(
    tmp_path: Path,
    file_name: str,
    content: bytes,
    message: str,
):
    sha = "e" * 40
    archive = _archive_bytes({file_name: content})

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=archive)

    request = ToolActionRequest(
        tool_name="github.download_snapshot",
        action="download",
        resource="https://github.com/example/project",
        arguments={"commit_sha": sha},
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GitHubRepositoryError, match=message):
            download_github_snapshot(
                request,
                approval_id=f"approval-{message}",
                data_dir=tmp_path,
                constraints=evaluate_tool_request(request).constraints,
                http_client=client,
            )


def _archive_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()
