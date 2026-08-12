"""Tests for ScopeFence."""

import pytest
from pathlib import Path
from agent.guardrails.fence import ScopeFence


@pytest.fixture
def fence(tmp_path):
    return ScopeFence(workspace=tmp_path)


def test_absolute_path_blocked(fence):
    result = fence.check("read_file", {"path": "/etc/hosts"})
    assert result.blocked


def test_relative_path_allowed(fence):
    result = fence.check("read_file", {"path": "src/main.py"})
    assert not result.blocked


def test_shell_etc_blocked(fence):
    result = fence.check("shell", {"cmd": "cat /etc/passwd"})
    assert result.blocked
    assert "/etc" in result.reason
