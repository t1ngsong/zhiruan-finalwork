"""Tests for ContextBuilder."""
import json
from pathlib import Path
from agent.config.loader import Config
from agent.tools import RiskLevel, ToolDefinition
from agent.tools.registry import ToolRegistry
from agent.memory.store import MemoryStore
from agent.context import ContextBuilder


def test_build_system_prompt_contains_tools_schema(tmp_path):
    """系统提示中包含工具 schema"""
    config = Config(workspace=str(tmp_path))
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="shell", description="执行命令",
        parameters={"cmd": {"type": "string"}},
        risk_level=RiskLevel.LOW,
        handler=lambda cmd: "",
    ))
    memory = MemoryStore(tmp_path)

    builder = ContextBuilder(config, registry, memory)
    prompt = builder.build_system_prompt()

    assert "shell" in prompt
    assert "cmd" in prompt
    assert "Coding Agent" in prompt or "编码任务" in prompt


def test_build_system_prompt_contains_rules(tmp_path):
    """系统提示中包含项目约定"""
    config = Config(workspace=str(tmp_path))
    registry = ToolRegistry()
    memory = MemoryStore(tmp_path)
    memory.set_rule("style", "use black formatter")
    memory.set_rule("lint", "use ruff")

    builder = ContextBuilder(config, registry, memory)
    prompt = builder.build_system_prompt()

    assert "style" in prompt
    assert "black formatter" in prompt
    assert "ruff" in prompt


def test_build_system_prompt_no_tools_shows_empty_schema(tmp_path):
    """无工具时显示空 schema"""
    config = Config(workspace=str(tmp_path))
    registry = ToolRegistry()
    memory = MemoryStore(tmp_path)

    builder = ContextBuilder(config, registry, memory)
    prompt = builder.build_system_prompt()

    assert "[]" in prompt  # empty JSON array


def test_build_system_prompt_contains_decisions(tmp_path):
    """系统提示中包含最近决策"""
    config = Config(workspace=str(tmp_path))
    registry = ToolRegistry()
    memory = MemoryStore(tmp_path)
    memory.record_decision("read_file(x)", "成功读取文件", approved=True)
    memory.record_decision("write_file(y, c)", "写入成功", approved=True)

    builder = ContextBuilder(config, registry, memory)
    prompt = builder.build_system_prompt()

    assert "最近决策" in prompt
    assert "read_file" in prompt
    assert "write_file" in prompt
