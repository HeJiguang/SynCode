from app.domain.tool_permissions import (
    ToolActionRequest,
    ToolPolicyDecision,
    ToolRiskLevel,
    evaluate_tool_request,
)


def test_public_github_metadata_is_read_only_and_auto_allowed():
    result = evaluate_tool_request(
        ToolActionRequest(
            tool_name="github.inspect_repository",
            action="inspect",
            resource="openai/openai-python.git",
        )
    )

    assert result.decision is ToolPolicyDecision.AUTO_ALLOW
    assert result.risk_level is ToolRiskLevel.LOW
    assert result.normalized_resource == "https://github.com/openai/openai-python"


def test_github_snapshot_requires_exact_commit_and_one_time_approval():
    result = evaluate_tool_request(
        ToolActionRequest(
            tool_name="github.download_snapshot",
            action="download",
            resource="https://github.com/openai/openai-python",
            arguments={"commit_sha": "a" * 40},
        )
    )

    assert result.decision is ToolPolicyDecision.ASK_USER
    assert result.constraints["approvalScope"] == "once"
    assert result.constraints["allowExecution"] is False
    assert result.normalized_resource.endswith("@" + "a" * 40)


def test_github_download_rejects_unpinned_or_non_github_sources():
    unpinned = evaluate_tool_request(
        ToolActionRequest(
            tool_name="github.download_snapshot",
            action="download",
            resource="https://github.com/openai/openai-python",
        )
    )
    internal = evaluate_tool_request(
        ToolActionRequest(
            tool_name="github.download_snapshot",
            action="download",
            resource="http://127.0.0.1/private",
            arguments={"commit_sha": "b" * 40},
        )
    )

    assert unpinned.decision is ToolPolicyDecision.BLOCK
    assert internal.decision is ToolPolicyDecision.BLOCK


def test_host_shell_and_unknown_tools_are_never_available_to_tutor():
    shell = evaluate_tool_request(ToolActionRequest(tool_name="host.shell", action="run"))
    unknown = evaluate_tool_request(ToolActionRequest(tool_name="github.delete_repository", action="delete"))

    assert shell.risk_level is ToolRiskLevel.PROHIBITED
    assert shell.decision is ToolPolicyDecision.BLOCK
    assert unknown.decision is ToolPolicyDecision.BLOCK

