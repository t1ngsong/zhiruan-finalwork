# tests/demo/test_demo_guardrail.py
"""机制演示①: 治理护栏拦截危险动作

此测试使用 MockLLMAdapter，确定性地演示:
1. Agent 收到 coding 任务
2. Agent 尝试执行 "rm -rf /"
3. 护栏识别为 FATAL 并拦截
4. 拦截信息回灌给 Agent
5. Agent 收到反馈后调整行为 (回复 FINISH)
"""

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


def test_guardrail_blocks_fatal_command(tmp_path):
    """
    Mock LLM 预设脚本:
    - 第1轮: 调用 shell "rm -rf /" (危险命令)
    - 第2轮: 收到拦截反馈，回复 FINISH
    """
    llm = MockLLMAdapter([
        # 第1轮: 尝试危险命令
        LLMResponse(
            content="我来删除旧的构建文件",
            tool_calls=[{"name": "shell", "arguments": '{"cmd": "rm -rf / --no-preserve-root"}'}],
            finish_reason="tool_calls",
        ),
        # 第2轮: 被拦截后收到反馈
        LLMResponse(content="FINISH: 危险操作已被护栏拦截", finish_reason="stop"),
    ])

    config = Config(workspace=str(tmp_path))

    # 注册 shell 工具
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="shell", description="执行命令",
        parameters={"cmd": {"type": "string"}},
        risk_level=RiskLevel.LOW,
        handler=lambda cmd: f"executed: {cmd}",
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

    result = agent.run("清理项目构建产物")

    # 验证
    assert result.success  # Agent 正常结束
    assert result.summary  # 包含拦截信息
    assert llm.call_count == 2  # 调用了两轮

    # 验证决策日志中有拦截记录
    decisions = memory.get_recent_decisions(10)
    blocked_decisions = [d for d in decisions if "拦截" in d.get("result_summary", "")]
    assert len(blocked_decisions) > 0
