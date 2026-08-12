"""Tests for ToolRegistry."""

import pytest
from agent.tools import ToolDefinition, RiskLevel, register_all_tools
from agent.tools.registry import ToolRegistry


def fake_handler(**kwargs):
    return "ok"


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = ToolDefinition(
            name="read_file",
            description="Read a file",
            parameters={"path": {"type": "string"}},
            risk_level=RiskLevel.LOW,
            handler=fake_handler,
        )
        registry.register(tool)
        assert registry.get("read_file") is tool

    def test_get_nonexistent(self):
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_get_schemas_for_llm(self):
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="read_file",
            description="Read a file",
            parameters={"path": {"type": "string", "description": "File path"}},
            risk_level=RiskLevel.LOW,
            handler=fake_handler,
        ))
        schemas = registry.get_schemas_for_llm()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "read_file"
        assert schemas[0]["description"] == "Read a file"
        assert "parameters" in schemas[0]
        assert schemas[0]["parameters"]["type"] == "object"
        assert "path" in schemas[0]["parameters"]["properties"]
        assert "path" in schemas[0]["parameters"]["required"]

    def test_get_schemas_for_llm_empty(self):
        registry = ToolRegistry()
        schemas = registry.get_schemas_for_llm()
        assert schemas == []

    def test_get_schemas_for_llm_multiple_tools(self):
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="read_file",
            description="Read a file",
            parameters={"path": {"type": "string"}},
            risk_level=RiskLevel.LOW,
            handler=fake_handler,
        ))
        registry.register(ToolDefinition(
            name="write_file",
            description="Write a file",
            parameters={"path": {"type": "string"}, "content": {"type": "string"}},
            risk_level=RiskLevel.MEDIUM,
            handler=fake_handler,
        ))
        schemas = registry.get_schemas_for_llm()
        assert len(schemas) == 2
        names = {s["name"] for s in schemas}
        assert names == {"read_file", "write_file"}


class TestRegisterAllTools:
    def test_registers_all_four_tools(self, temp_workspace):
        registry = ToolRegistry()
        register_all_tools(registry, temp_workspace)
        schemas = registry.get_schemas_for_llm()
        names = {s["name"] for s in schemas}
        assert names == {"read_file", "write_file", "shell", "search"}
        assert len(schemas) == 4

    def test_read_file_via_registry(self, temp_workspace, sample_file):
        registry = ToolRegistry()
        register_all_tools(registry, temp_workspace)
        tool = registry.get("read_file")
        result = tool.handler(path="hello.py")
        assert "def hello()" in result

    def test_write_file_via_registry(self, temp_workspace):
        registry = ToolRegistry()
        register_all_tools(registry, temp_workspace)
        tool = registry.get("write_file")
        result = tool.handler(path="new.py", content="x = 1")
        assert (temp_workspace / "new.py").read_text() == "x = 1"

    def test_shell_via_registry(self, temp_workspace):
        registry = ToolRegistry()
        register_all_tools(registry, temp_workspace)
        tool = registry.get("shell")
        result = tool.handler(cmd="echo hello")
        assert "hello" in result

    def test_search_via_registry(self, temp_workspace, sample_file):
        registry = ToolRegistry()
        register_all_tools(registry, temp_workspace)
        tool = registry.get("search")
        result = tool.handler(pattern="hello")
        assert "hello" in result.lower()

    def test_all_tools_have_valid_risk_levels(self, temp_workspace):
        registry = ToolRegistry()
        register_all_tools(registry, temp_workspace)
        for name in ["read_file", "write_file", "shell", "search"]:
            tool = registry.get(name)
            assert tool is not None
            assert isinstance(tool.risk_level, RiskLevel)
