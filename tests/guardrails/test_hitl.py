"""Tests for HITLGate state machine and timeout."""

import threading
import time

from agent.tools import RiskLevel
from agent.guardrails.hitl import HITLGate
from agent.guardrails import RiskResult
from unittest.mock import patch


# ── FATAL / LOW auto-decisions ──────────────────────────────────────────────

def test_fatal_auto_reject():
    gate = HITLGate()
    result = gate.request_approval("shell", {"cmd": "rm -rf /"},
                                    RiskResult(RiskLevel.FATAL, "危险"))
    assert result is False


def test_fatal_sets_state_rejected():
    gate = HITLGate()
    gate.request_approval("shell", {"cmd": "rm -rf /"},
                          RiskResult(RiskLevel.FATAL, "危险"))
    assert gate.state == "REJECTED"


def test_low_auto_approve():
    gate = HITLGate()
    result = gate.request_approval("read_file", {"path": "x.py"},
                                    RiskResult(RiskLevel.LOW, ""))
    assert result is True


def test_low_sets_state_approved():
    gate = HITLGate()
    gate.request_approval("read_file", {"path": "x.py"},
                          RiskResult(RiskLevel.LOW, ""))
    assert gate.state == "APPROVED"


# ── State resets on next call ────────────────────────────────────────────────

@patch("builtins.input", return_value="y")
def test_state_resets_to_idle_on_next_call(mock_input):
    gate = HITLGate()
    # First call: FATAL, state becomes REJECTED
    gate.request_approval("shell", {"cmd": "rm -rf /"},
                          RiskResult(RiskLevel.FATAL, "危险"))
    assert gate.state == "REJECTED"

    # Second call: LOW, should reset to IDLE first, then APPROVED
    gate.request_approval("read_file", {"path": "x.py"},
                          RiskResult(RiskLevel.LOW, ""))
    assert gate.state == "APPROVED"


# ── MEDIUM/HIGH: user decisions ─────────────────────────────────────────────

@patch("builtins.input", return_value="y")
def test_high_user_approves(mock_input):
    gate = HITLGate()
    result = gate.request_approval("shell", {"cmd": "git push --force"},
                                    RiskResult(RiskLevel.HIGH, "强制推送"))
    assert result is True


@patch("builtins.input", return_value="y")
def test_high_user_approves_state_approved(mock_input):
    gate = HITLGate()
    gate.request_approval("shell", {"cmd": "git push --force"},
                          RiskResult(RiskLevel.HIGH, "强制推送"))
    assert gate.state == "APPROVED"


@patch("builtins.input", return_value="n")
def test_high_user_rejects(mock_input):
    gate = HITLGate()
    result = gate.request_approval("shell", {"cmd": "git push --force"},
                                    RiskResult(RiskLevel.HIGH, "强制推送"))
    assert result is False


@patch("builtins.input", return_value="n")
def test_high_user_rejects_state_rejected(mock_input):
    gate = HITLGate()
    gate.request_approval("shell", {"cmd": "git push --force"},
                          RiskResult(RiskLevel.HIGH, "强制推送"))
    assert gate.state == "REJECTED"


@patch("builtins.input", return_value="")
def test_empty_input_treated_as_reject(mock_input):
    gate = HITLGate()
    result = gate.request_approval("shell", {"cmd": "git push --force"},
                                    RiskResult(RiskLevel.HIGH, "强制推送"))
    assert result is False
    assert gate.state == "REJECTED"


# ── Timeout ──────────────────────────────────────────────────────────────────

def test_timeout_returns_false():
    """When input times out, request_approval returns False."""
    gate = HITLGate(timeout=0)  # Immediate timeout
    result = gate.request_approval("shell", {"cmd": "git push --force"},
                                    RiskResult(RiskLevel.HIGH, "强制推送"))
    assert result is False


def test_timeout_sets_state_timeout():
    """When input times out, state is set to TIMEOUT."""
    gate = HITLGate(timeout=0)
    gate.request_approval("shell", {"cmd": "git push --force"},
                          RiskResult(RiskLevel.HIGH, "强制推送"))
    assert gate.state == "TIMEOUT"


def test_input_before_timeout_does_not_timeout():
    """Input received before timeout should not trigger TIMEOUT."""
    gate = HITLGate(timeout=5)
    # The mock patches input so it returns immediately -- should not timeout
    with patch("builtins.input", return_value="y"):
        gate.request_approval("shell", {"cmd": "git push --force"},
                              RiskResult(RiskLevel.HIGH, "强制推送"))
    assert gate.state == "APPROVED"


# ── WAITING state is transient ──────────────────────────────────────────────

@patch("builtins.input", return_value="y")
def test_state_is_approved_after_approval_not_waiting(mock_input):
    """After user approves, state should be APPROVED, not WAITING."""
    gate = HITLGate()
    gate.request_approval("shell", {"cmd": "sudo ls"},
                          RiskResult(RiskLevel.MEDIUM, "提权操作"))
    assert gate.state == "APPROVED"
