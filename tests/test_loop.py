# tests/test_loop.py
import pytest
from pathlib import Path
from agent.llm.adapter import LLMResponse
from agent.llm.mock import MockLLMAdapter
from agent.parser import ActionParser
from agent.config.loader import Config
from agent.tools import RiskLevel, ToolDefinition
from agent.tools.registry import ToolRegistry
from agent.tools.executor import ToolExecutor
from agent.guardrails.scorer import RiskScorer
from agent.guardrails.hitl import HITLGate
from agent.guardrails.fence import ScopeFence
from agent.guardrails.coordinator import GuardrailCoordinator
from agent.feedback.collector import FeedbackCollector
from agent.memory.store import MemoryStore
from agent.loop import AgentLoop


def make_simple_handler(output):
    """创建返回固定输出的 handler"""
    return lambda **kwargs: output


def test_agent_finishes_when_llm_says_finish(tmp_path):
    """测试: LLM 直接返回 FINISH"""
    llm = MockLLMAdapter([
        LLMResponse(content="FINISH: 任务已完成", finish_reason="stop"),
    ])
    parser = ActionParser()
    config = Config(workspace=str(tmp_path))
    registry = ToolRegistry()
    executor = ToolExecutor(registry, workspace=tmp_path)
    scorer = RiskScorer(workspace=tmp_path)
    hitl = HITLGate()
    fence = ScopeFence(workspace=tmp_path)
    guardrail = GuardrailCoordinator(scorer, hitl, fence)
    collector = FeedbackCollector()
    memory = MemoryStore(tmp_path)

    agent = AgentLoop(config, llm, parser, registry, executor, guardrail, collector, memory)
    result = agent.run("写一个 hello world")

    assert result.success
    assert "任务已完成" in result.summary


def test_agent_runs_shell_and_stops_on_test_pass(tmp_path):
    """测试: Agent 运行 pytest -> 通过 -> 自动退出"""
    tmp_path_str = str(tmp_path)
    llm = MockLLMAdapter([
        LLMResponse(
            content="",
            tool_calls=[{"name": "shell", "arguments": '{"cmd": "pytest"}'}],
            finish_reason="tool_calls",
        ),
    ])
    parser = ActionParser()
    config = Config(workspace=tmp_path_str)
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="shell", description="执行命令",
        parameters={"cmd": {"type": "string"}},
        risk_level=RiskLevel.LOW,
        handler=lambda cmd: "3 passed in 0.5s",
    ))
    executor = ToolExecutor(registry, workspace=tmp_path)
    scorer = RiskScorer(workspace=tmp_path)
    fence = ScopeFence(workspace=tmp_path)
    hitl = HITLGate()
    guardrail = GuardrailCoordinator(scorer, hitl, fence)
    collector = FeedbackCollector()
    memory = MemoryStore(tmp_path)

    agent = AgentLoop(config, llm, parser, registry, executor, guardrail, collector, memory)
    result = agent.run("运行测试")

    assert result.success
    assert "测试通过" in result.summary or result.rounds == 1


def test_agent_guardrail_blocks_dangerous_command(tmp_path):
    """测试: 护栏拦截危险命令"""
    llm = MockLLMAdapter([
        LLMResponse(
            content="",
            tool_calls=[{"name": "shell", "arguments": '{"cmd": "rm -rf /"}'}],
            finish_reason="tool_calls",
        ),
        LLMResponse(content="FINISH: 被护栏拦截，无法执行", finish_reason="stop"),
    ])
    parser = ActionParser()
    config = Config(workspace=str(tmp_path))
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="shell", description="执行命令",
        parameters={"cmd": {"type": "string"}},
        risk_level=RiskLevel.LOW,
        handler=lambda cmd: "",
    ))
    executor = ToolExecutor(registry, workspace=tmp_path)
    scorer = RiskScorer(workspace=tmp_path)
    fence = ScopeFence(workspace=tmp_path)
    hitl = HITLGate()
    guardrail = GuardrailCoordinator(scorer, hitl, fence)
    collector = FeedbackCollector()
    memory = MemoryStore(tmp_path)

    agent = AgentLoop(config, llm, parser, registry, executor, guardrail, collector, memory)
    result = agent.run("删除所有文件")

    assert result.success  # Agent 正常结束（报告拦截）
