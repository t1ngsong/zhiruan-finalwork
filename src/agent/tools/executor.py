"""ToolExecutor: dispatches tool calls to registered handlers."""

from pathlib import Path
from agent.tools.registry import ToolRegistry
from agent.tools import ToolResult


class ToolExecutor:
    """Executes tool calls by dispatching to registered handlers.

    The executor resolves the tool by name, invokes the handler with
    the provided arguments, and wraps the result in a ToolResult.
    """

    def __init__(self, registry: ToolRegistry, workspace: Path):
        self.registry = registry
        self.workspace = Path(workspace).resolve()

    def execute_tool(self, tool_name: str, args: dict) -> ToolResult:
        """Execute a tool by name with the given arguments."""
        tool = self.registry.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False, exit_code=-1,
                error=f"Unknown tool: {tool_name}", tool_name=tool_name,
            )
        try:
            output = tool.handler(**args)
            return ToolResult(
                success=True, exit_code=0,
                stdout=str(output) if output else "",
                tool_name=tool_name,
            )
        except Exception as e:
            return ToolResult(
                success=False, exit_code=-1,
                error=f"{type(e).__name__}: {e}", tool_name=tool_name,
            )
