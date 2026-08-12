"""Scope fence: blocks access to system directories and absolute paths."""

from pathlib import Path
from agent.guardrails import GuardResult


class ScopeFence:
    """Blocks tool calls that attempt to access paths outside the workspace.

    - Shell commands containing /etc, /sys, /proc, /boot, /dev are blocked
    - read_file / write_file / search with absolute paths are blocked
    """

    DENY_PREFIXES = [
        "/etc", "/sys", "/proc", "/boot", "/dev",
    ]

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).resolve()

    def check(self, tool_name: str, args: dict) -> GuardResult:
        # Shell: check for system directory access
        if tool_name == "shell":
            cmd = args.get("cmd", "")
            for prefix in self.DENY_PREFIXES:
                if prefix in cmd:
                    return GuardResult(blocked=True, reason=f"禁止访问系统目录: {prefix}")

        # File tools: block absolute paths
        if tool_name in ("read_file", "write_file", "search"):
            path_str = args.get("path", "")
            if path_str.startswith("/"):
                return GuardResult(blocked=True, reason=f"禁止使用绝对路径: {path_str}")

        return GuardResult(blocked=False)
