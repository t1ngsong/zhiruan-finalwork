# tests/demo/test_demo_deep.py
"""机制演示③: 重点维度深度行为 — 自定义护栏规则 + 审批机制

此测试确定性地演示:
1. 用户在 .agent.yaml 中自定义了危险模式: "deploy --production" 为 HIGH
2. Agent 尝试执行 "deploy --production"
3. 护栏识别为 HIGH → 触发 HITL 审批
4. 用户拒绝 → 操作被阻止
5. 用户批准另一低风险操作 → 正常执行
"""

from pathlib import Path
from unittest.mock import patch
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


def test_custom_guardrail_pattern_with_approval(tmp_path):
    """自定义护栏规则: deploy --production 需要审批"""

    custom_patterns = [
        {"pattern": r"deploy\s+--production", "level": "HIGH", "reason": "生产环境部署需人工确认"},
    ]

    llm = MockLLMAdapter([
        # 第1轮: 尝试部署到生产环境
        LLMResponse(
            content="",
            tool_calls=[{"name": "shell", "arguments": '{"cmd": "deploy --production --region us-east-1"}'}],
            finish_reason="tool_calls",
        ),
        # 第2轮: 审批被拒 → Agent 收到反馈 → 回复 FINISH
        LLMResponse(content="FINISH: 生产部署需要审批，用户拒绝了", finish_reason="stop"),
    ])

    config = Config(workspace=str(tmp_path), custom_patterns=custom_patterns)

    executed_commands = []

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="shell", description="执行命令",
        parameters={"cmd": {"type": "string"}},
        risk_level=RiskLevel.LOW,
        handler=lambda cmd: executed_commands.append(cmd) or "executed",
    ))

    parser = ActionParser()
    executor = ToolExecutor(registry, tmp_path)
    scorer = RiskScorer(tmp_path, custom_patterns=custom_patterns)
    hitl = HITLGate()
    fence = ScopeFence(tmp_path)
    guardrail = GuardrailCoordinator(scorer, hitl, fence)
    collector = FeedbackCollector()
    memory = MemoryStore(tmp_path)

    agent = AgentLoop(config, llm, parser, registry, executor, guardrail, collector, memory)

    # 验证自定义模式被正确识别
    risk = scorer.score("shell", {"cmd": "deploy --production --region us-east-1"})
    assert risk.level == RiskLevel.HIGH
    assert "生产环境" in risk.reason

    # 模拟用户拒绝审批
    with patch("builtins.input", return_value="n"):
        result = agent.run("部署到生产环境")

    assert result.success
    # 危险命令不应该被执行
    assert len(executed_commands) == 0


def test_custom_pattern_low_risk_allowed(tmp_path):
    """自定义 low 风险模式: 已确认安全的 rm -rf 某个目录"""

    custom_patterns = [
        {"pattern": r"rm -rf /tmp/myapp/build", "level": "LOW", "reason": "已确认安全的构建清理"},
    ]

    scorer = RiskScorer(tmp_path, custom_patterns=custom_patterns)
    risk = scorer.score("shell", {"cmd": "rm -rf /tmp/myapp/build"})
    assert risk.level == RiskLevel.LOW
