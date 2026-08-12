# tests/demo/test_demo_feedback.py
"""机制演示②: 反馈闭环使 Agent 收到失败信号并改变下一步动作

此测试使用 MockLLMAdapter，确定性地演示:
1. Agent 运行 pytest → 2 passed, 1 failed
2. 反馈收集器解析出测试失败
3. 反馈回灌给 Agent
4. Agent 在下一轮读取失败测试所在的文件并修复
5. Agent 再次运行 pytest → 3 passed (全部通过)
6. 停机判断器检测到全部通过 → 自动退出
"""

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


def test_feedback_drives_self_correction(tmp_path):
    """
    模拟: 测试失败 → Agent 修复 → 测试通过

    Mock LLM 预设脚本:
    - 第1轮: 运行 pytest
    - 第2轮: 收到失败反馈 → 读取失败文件
    - 第3轮: 修复代码
    - 第4轮: 再次运行 pytest
    """
    # 创建一个真实的测试文件（模拟失败测试）
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_calc.py").write_text("""
def test_add():
    assert 1 + 1 == 3  # 故意写错的测试
""")

    llm = MockLLMAdapter([
        # 第1轮: 运行测试
        LLMResponse(
            content="",
            tool_calls=[{"name": "shell", "arguments": '{"cmd": "pytest tests/ -v"}'}],
            finish_reason="tool_calls",
        ),
        # 第2轮: 收到 "1 failed" 反馈 → 读取失败文件
        LLMResponse(
            content="",
            tool_calls=[{"name": "read_file", "arguments": '{"path": "tests/test_calc.py"}'}],
            finish_reason="tool_calls",
        ),
        # 第3轮: 修复测试
        LLMResponse(
            content="",
            tool_calls=[{"name": "write_file", "arguments": '{"path": "tests/test_calc.py", "content": "def test_add():\\n    assert 1 + 1 == 2\\n"}'}],
            finish_reason="tool_calls",
        ),
        # 第4轮: 再次运行测试
        LLMResponse(
            content="",
            tool_calls=[{"name": "shell", "arguments": '{"cmd": "pytest tests/ -v"}'}],
            finish_reason="tool_calls",
        ),
    ])

    config = Config(workspace=str(tmp_path))

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="shell", description="执行命令",
        parameters={"cmd": {"type": "string"}},
        risk_level=RiskLevel.LOW,
        handler=lambda cmd: _simulate_pytest(cmd, tmp_path),
    ))
    registry.register(ToolDefinition(
        name="read_file", description="读取文件",
        parameters={"path": {"type": "string"}},
        risk_level=RiskLevel.LOW,
        handler=lambda path: (tmp_path / path).read_text(),
    ))
    registry.register(ToolDefinition(
        name="write_file", description="写入文件",
        parameters={"path": {"type": "string"}, "content": {"type": "string"}},
        risk_level=RiskLevel.MEDIUM,
        handler=lambda path, content: _write_file(tmp_path, path, content),
    ))

    parser = ActionParser()
    executor = ToolExecutor(registry, tmp_path)
    scorer = RiskScorer(tmp_path)
    hitl = HITLGate()
    fence = ScopeFence(tmp_path)
    guardrail = GuardrailCoordinator(scorer, hitl, fence)
    collector = FeedbackCollector()
    memory = MemoryStore(tmp_path)

    agent = AgentLoop(config, llm, parser, registry, executor, guardrail, collector, memory)

    result = agent.run("修复测试失败")

    # 验证 Agent 完成了多轮自我修正过程
    assert result.rounds >= 2  # 至少经历了两轮
    # 验证测试文件被修复
    fixed = (tmp_path / "tests" / "test_calc.py").read_text()
    assert "1 + 1 == 2" in fixed


# -- 模拟辅助函数 --

_call_counter = {"pytest": 0}


@pytest.fixture(autouse=True)
def _reset_counter():
    """每个测试前重置计数器"""
    _call_counter["pytest"] = 0


def _simulate_pytest(cmd, tmp_path):
    """模拟 pytest: 第一次返回失败，第二次返回通过"""
    if "pytest" in cmd:
        _call_counter["pytest"] += 1
        if _call_counter["pytest"] == 1:
            return "test_calc.py::test_add FAILED\n======= 1 failed in 0.1s ======="
        else:
            return "test_calc.py::test_add PASSED\n======= 1 passed in 0.1s ======="
    return ""


def _write_file(tmp_path, path, content):
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"已写入 {target}"
