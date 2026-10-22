from pathlib import Path


def authorize_tool(tool: str, approved_tools: set[str]) -> tuple[str, str]:
    if tool not in approved_tools:
        return "deny", "tool_not_approved"
    return "allow", "approved"


def test_unapproved_command_is_denied_without_execution(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    decision, reason = authorize_tool("shell.exec", {"build_submission"})

    assert (decision, reason) == ("deny", "tool_not_approved")
    assert not marker.exists()
