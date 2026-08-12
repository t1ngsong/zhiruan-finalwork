"""Tests for GuardrailCoordinator."""

import pytest
from pathlib import Path
from agent.tools import RiskLevel
from agent.guardrails.scorer import RiskScorer
from agent.guardrails.hitl import HITLGate
from agent.guardrails.fence import ScopeFence
from agent.guardrails.coordinator import GuardrailCoordinator
from unittest.mock import patch


@pytest.fixture
def coordinator(tmp_path):
    scorer = RiskScorer(workspace=tmp_path)
    hitl = HITLGate(timeout=60)
    fence = ScopeFence(workspace=tmp_path)
    return GuardrailCoordinator(scorer, hitl, fence)


def test_safe_read_passes(coordinator):
    result = coordinator.check("read_file", {"path": "main.py"})
    assert not result.blocked


def test_fatal_shell_blocked(coordinator):
    result = coordinator.check("shell", {"cmd": "rm -rf /"})
    assert result.blocked
    assert "致命" in result.reason


def test_write_outside_workspace_blocked(coordinator):
    result = coordinator.check("write_file", {"path": "/tmp/evil.sh"})
    assert result.blocked
