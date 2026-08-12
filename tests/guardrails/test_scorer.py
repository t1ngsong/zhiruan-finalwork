"""Tests for RiskScorer."""

import pytest
from pathlib import Path
from agent.tools import RiskLevel
from agent.guardrails.scorer import RiskScorer


@pytest.fixture
def scorer(tmp_path):
    return RiskScorer(workspace=tmp_path)


def test_read_file_is_low(scorer):
    result = scorer.score("read_file", {"path": "test.py"})
    assert result.level == RiskLevel.LOW


def test_search_is_low(scorer):
    result = scorer.score("search", {"pattern": "TODO", "path": "."})
    assert result.level == RiskLevel.LOW


def test_write_within_workspace_is_low(scorer):
    result = scorer.score("write_file", {"path": "new.py"})
    assert result.level == RiskLevel.LOW


def test_write_outside_workspace_is_fatal(scorer):
    result = scorer.score("write_file", {"path": "/etc/passwd"})
    assert result.level == RiskLevel.FATAL


def test_shell_rm_rf_is_fatal(scorer):
    result = scorer.score("shell", {"cmd": "rm -rf / --no-preserve-root"})
    assert result.level == RiskLevel.FATAL


def test_shell_pytest_is_low(scorer):
    result = scorer.score("shell", {"cmd": "pytest tests/"})
    assert result.level == RiskLevel.LOW
