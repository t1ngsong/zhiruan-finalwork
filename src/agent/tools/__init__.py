"""Tool system: definitions, registry, executor, and built-in tools."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class RiskLevel(str, Enum):
    """Risk level for tool execution."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    FATAL = "FATAL"


@dataclass
class ToolResult:
    """Result of executing a tool."""
    success: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    tool_name: str = ""


@dataclass
class ToolDefinition:
    """Definition of a tool that can be registered in the ToolRegistry."""
    name: str
    description: str
    parameters: dict[str, Any]
    risk_level: RiskLevel
    handler: Callable[..., Any]


def register_all_tools(registry, workspace: Path,
                       file_tools_enabled: bool = True,
                       shell_enabled: bool = True,
                       search_enabled: bool = True,
                       shell_timeout: int = 30) -> None:
    """Register all built-in tools into a ToolRegistry with workspace bound.

    This is the wiring function that connects the tool handler functions
    to the registry, binding the workspace for confinement.

    Individual tool categories can be disabled via the *_enabled flags.
    """
    from agent.tools.file_tools import read_file, write_file
    from agent.tools.shell_tool import execute_shell
    from agent.tools.search_tool import search

    if file_tools_enabled:
        registry.register(ToolDefinition(
            name="read_file",
            description="Read the contents of a file within the workspace",
            parameters={
                "path": {
                    "type": "string",
                    "description": "Relative path to the file within the workspace",
                },
            },
            risk_level=RiskLevel.LOW,
            handler=lambda path: read_file(workspace, path),
        ))

        registry.register(ToolDefinition(
            name="write_file",
            description="Write content to a file within the workspace (overwrites if exists)",
            parameters={
                "path": {
                    "type": "string",
                    "description": "Relative path to the file within the workspace",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write to the file",
                },
            },
            risk_level=RiskLevel.MEDIUM,
            handler=lambda path, content: write_file(workspace, path, content),
        ))

    if shell_enabled:
        registry.register(ToolDefinition(
            name="shell",
            description="Execute a shell command within the workspace directory",
            parameters={
                "cmd": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds (default 30)",
                },
            },
            risk_level=RiskLevel.HIGH,
            handler=lambda cmd, timeout=shell_timeout: _shell_handler(workspace, cmd, timeout),
        ))

    if search_enabled:
        registry.register(ToolDefinition(
            name="search",
            description="Search for a text pattern in Python files within the workspace",
            parameters={
                "pattern": {
                    "type": "string",
                    "description": "The text pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Subdirectory to search (default '.' for all)",
                },
            },
            risk_level=RiskLevel.LOW,
            handler=lambda pattern, path=".": search(workspace, pattern, path),
        ))


def _shell_handler(workspace: Path, cmd: str, timeout: int = 30) -> str:
    """Wrapper that adapts execute_shell's dict return to a string for ToolResult."""
    from agent.tools.shell_tool import execute_shell
    result = execute_shell(workspace, cmd, timeout)
    if result["success"]:
        return result["stdout"]
    else:
        return result["stderr"] or f"Command failed with exit code {result['exit_code']}"
