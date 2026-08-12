"""Tests for ToolExecutor."""

import pytest
from pathlib import Path
from agent.tools import ToolResult, RiskLevel, ToolDefinition
from agent.tools.registry import ToolRegistry
from agent.tools.executor import ToolExecutor


class TestToolExecutor:
    def test_execute_known_tool(self, temp_workspace):
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="read_file",
            description="Read a file",
            parameters={"path": {"type": "string"}},
            risk_level=RiskLevel.LOW,
            handler=lambda path: Path(path).read_text(),
        ))
        executor = ToolExecutor(registry, workspace=temp_workspace)
        f = temp_workspace / "test.txt"
        f.write_text("hello")
        result = executor.execute_tool("read_file", {"path": str(f)})
        assert result.success
        assert result.stdout == "hello"
        assert result.tool_name == "read_file"

    def test_execute_unknown_tool(self, temp_workspace):
        executor = ToolExecutor(ToolRegistry(), workspace=temp_workspace)
        result = executor.execute_tool("nonexistent", {})
        assert not result.success
        assert "Unknown tool" in result.error or "未知工具" in result.error

    def test_execute_with_exception(self, temp_workspace):
        registry = ToolRegistry()
        def failing_handler(**kwargs):
            raise ValueError("simulated error")
        registry.register(ToolDefinition(
            name="bad", description="will fail",
            parameters={}, risk_level=RiskLevel.LOW,
            handler=failing_handler,
        ))
        executor = ToolExecutor(registry, workspace=temp_workspace)
        result = executor.execute_tool("bad", {})
        assert not result.success
        assert "ValueError" in result.error

    def test_execute_tool_with_no_args(self, temp_workspace):
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="ping",
            description="Returns pong",
            parameters={},
            risk_level=RiskLevel.LOW,
            handler=lambda: "pong",
        ))
        executor = ToolExecutor(registry, workspace=temp_workspace)
        result = executor.execute_tool("ping", {})
        assert result.success
        assert result.stdout == "pong"

    def test_execute_tool_returns_none(self, temp_workspace):
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="noop",
            description="Does nothing",
            parameters={},
            risk_level=RiskLevel.LOW,
            handler=lambda: None,
        ))
        executor = ToolExecutor(registry, workspace=temp_workspace)
        result = executor.execute_tool("noop", {})
        assert result.success
        assert result.stdout == ""

    def test_workspace_is_resolved(self, temp_workspace):
        registry = ToolRegistry()
        executor = ToolExecutor(registry, workspace=temp_workspace)
        assert executor.workspace == temp_workspace.resolve()
