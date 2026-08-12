"""ToolRegistry: registers and looks up tool definitions."""

from agent.tools import ToolDefinition


class ToolRegistry:
    """Registry for tool definitions.

    Tools are registered by name and can be retrieved individually
    or as LLM-compatible JSON schemas.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name, or None if not found."""
        return self._tools.get(name)

    def get_schemas_for_llm(self) -> list[dict]:
        """Return tool definitions formatted as LLM function-calling schemas."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": {
                    "type": "object",
                    "properties": t.parameters,
                    "required": list(t.parameters.keys()),
                },
            }
            for t in self._tools.values()
        ]
