"""Guardrail coordinator: orchestrates all 4 guardrail layers.

Layer order: ScopeFence -> RiskScorer -> (FATAL reject) -> HITLGate
"""

from agent.guardrails.scorer import RiskScorer
from agent.guardrails.hitl import HITLGate
from agent.guardrails.fence import ScopeFence
from agent.guardrails import GuardResult
from agent.tools import RiskLevel


class GuardrailCoordinator:
    """Orchestrates the 4-layer guardrail pipeline.

    1. ScopeFence: block system access / absolute paths
    2. RiskScorer: score the tool call
    3. FATAL: auto-block
    4. HITLGate: prompt user for MEDIUM/HIGH risk
    """

    def __init__(self, scorer: RiskScorer, hitl: HITLGate, fence: ScopeFence):
        self.scorer = scorer
        self.hitl = hitl
        self.fence = fence

    def check(self, tool_name: str, args: dict) -> GuardResult:
        # 1. Scope fence
        fence_result = self.fence.check(tool_name, args)
        if fence_result.blocked:
            return fence_result

        # 2. Risk scoring
        risk = self.scorer.score(tool_name, args)

        # 3. FATAL → direct reject
        if risk.level == RiskLevel.FATAL:
            return GuardResult(blocked=True, reason=f"[致命] {risk.reason}")

        # 4. HITL approval (MEDIUM / HIGH)
        if risk.level in (RiskLevel.MEDIUM, RiskLevel.HIGH):
            approved = self.hitl.request_approval(tool_name, args, risk)
            if not approved:
                return GuardResult(blocked=True, reason=f"[审批] 用户拒绝了 {tool_name}")

        return GuardResult(blocked=False)
