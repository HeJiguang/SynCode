from enum import Enum
import re
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field


class ToolRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    PROHIBITED = "PROHIBITED"


class ToolPolicyDecision(str, Enum):
    AUTO_ALLOW = "AUTO_ALLOW"
    ASK_USER = "ASK_USER"
    BLOCK = "BLOCK"


class ToolApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    EXECUTED = "EXECUTED"


class ToolActionRequest(BaseModel):
    tool_name: str
    action: str
    resource: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolPolicyResult(BaseModel):
    decision: ToolPolicyDecision
    risk_level: ToolRiskLevel
    reason: str
    normalized_resource: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class ToolApproval(BaseModel):
    approval_id: str
    user_id: str
    conversation_id: str | None = None
    run_id: str
    hermes_run_id: str | None = None
    hermes_request_id: str | None = None
    tool_name: str
    action: str
    resource: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    risk_level: ToolRiskLevel
    decision: ToolPolicyDecision
    status: ToolApprovalStatus
    reason: str | None = None
    created_at: str
    expires_at: str | None = None
    resolved_at: str | None = None


_AUTO_READ_TOOLS = {
    "problem.get_context",
    "submission.get_summary",
    "conversation.get_history",
    "learning_profile.get_relevant",
    "problem.search",
}

_ALWAYS_BLOCKED_TOOLS = {
    "host.shell",
    "host.filesystem",
    "docker.socket",
    "secrets.read",
    "judge.hidden_tests",
    "database.raw_query",
    "network.arbitrary_fetch",
    "package.install",
}

_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
_GITHUB_SEGMENT = re.compile(r"^[A-Za-z0-9_.-]+$")


def evaluate_tool_request(request: ToolActionRequest) -> ToolPolicyResult:
    if request.tool_name in _ALWAYS_BLOCKED_TOOLS:
        return ToolPolicyResult(
            decision=ToolPolicyDecision.BLOCK,
            risk_level=ToolRiskLevel.PROHIBITED,
            reason="做题助手不允许访问宿主机、密钥、隐藏测试或任意执行环境。",
        )

    if request.tool_name in _AUTO_READ_TOOLS:
        return ToolPolicyResult(
            decision=ToolPolicyDecision.AUTO_ALLOW,
            risk_level=ToolRiskLevel.LOW,
            reason="只读取当前用户范围内的学习数据。",
        )

    if request.tool_name == "github.inspect_repository":
        resource = normalize_public_github_repository(request.resource)
        if resource is None:
            return _blocked_github_result()
        return ToolPolicyResult(
            decision=ToolPolicyDecision.AUTO_ALLOW,
            risk_level=ToolRiskLevel.LOW,
            reason="只读取公开仓库元数据，不下载或执行仓库内容。",
            normalized_resource=resource,
            constraints={"allowedHosts": ["api.github.com"], "credentials": False},
        )

    if request.tool_name == "github.download_snapshot":
        resource = normalize_public_github_repository(request.resource)
        commit_sha = str(request.arguments.get("commit_sha") or "")
        if resource is None or not _COMMIT_SHA.fullmatch(commit_sha):
            return _blocked_github_result("下载必须绑定公开仓库和固定的 40 位 commit SHA。")
        return ToolPolicyResult(
            decision=ToolPolicyDecision.ASK_USER,
            risk_level=ToolRiskLevel.MEDIUM,
            reason="外部源码将进入一次性沙箱，必须由用户针对本次操作确认。",
            normalized_resource=f"{resource}@{commit_sha.lower()}",
            constraints={
                "approvalScope": "once",
                "allowedHosts": ["api.github.com", "codeload.github.com"],
                "maxDownloadBytes": 100 * 1024 * 1024,
                "maxExtractedBytes": 200 * 1024 * 1024,
                "maxFiles": 5000,
                "allowSubmodules": False,
                "allowGitLfs": False,
                "allowExecution": False,
                "ttlSeconds": 1800,
            },
        )

    if request.tool_name in {"workspace.apply_patch", "sandbox.run_public_samples"}:
        return ToolPolicyResult(
            decision=ToolPolicyDecision.ASK_USER,
            risk_level=ToolRiskLevel.HIGH,
            reason="该操作会修改用户工作区或执行代码，必须单次确认并使用隔离沙箱。",
            normalized_resource=request.resource,
            constraints={"approvalScope": "once", "ttlSeconds": 300},
        )

    return ToolPolicyResult(
        decision=ToolPolicyDecision.BLOCK,
        risk_level=ToolRiskLevel.PROHIBITED,
        reason="工具未出现在 SynCode 做题助手的能力白名单中。",
    )


def normalize_public_github_repository(resource: str | None) -> str | None:
    if not resource:
        return None
    raw = resource.strip()
    if raw.endswith(".git"):
        raw = raw[:-4]
    parsed = urlparse(raw if "://" in raw else f"https://github.com/{raw.lstrip('/')}")
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.query or parsed.fragment:
        return None
    segments = [segment for segment in parsed.path.split("/") if segment]
    if len(segments) != 2 or not all(_GITHUB_SEGMENT.fullmatch(segment) for segment in segments):
        return None
    return f"https://github.com/{segments[0]}/{segments[1]}"


def _blocked_github_result(reason: str = "只允许读取 github.com 上格式合法的公开仓库。") -> ToolPolicyResult:
    return ToolPolicyResult(
        decision=ToolPolicyDecision.BLOCK,
        risk_level=ToolRiskLevel.PROHIBITED,
        reason=reason,
    )
