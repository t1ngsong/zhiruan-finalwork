"""Guardrail system: pattern matching, risk scoring, HITL, scope fencing."""

from dataclasses import dataclass
from agent.tools import RiskLevel


@dataclass
class RiskResult:
    """Result of risk scoring a tool call."""
    level: RiskLevel
    reason: str = ""


@dataclass
class GuardResult:
    """Result of a guardrail check."""
    blocked: bool
    reason: str = ""
