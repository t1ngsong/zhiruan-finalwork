"""Tests for shell_tool (execute_shell)."""

import pytest
from agent.tools.shell_tool import execute_shell


class TestExecuteShell:
    def test_execute_shell_success(self, temp_workspace):
        result = execute_shell(temp_workspace, "echo hello")
        assert result["success"]
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_execute_shell_failure(self, temp_workspace):
        result = execute_shell(temp_workspace, "exit 1")
        assert not result["success"]
        assert result["exit_code"] == 1

    def test_execute_shell_stderr(self, temp_workspace):
        result = execute_shell(temp_workspace, "echo error >&2")
        assert "error" in result["stderr"]

    def test_execute_shell_default_timeout(self, temp_workspace):
        result = execute_shell(temp_workspace, "echo ok")
        assert result["success"]

    def test_execute_shell_custom_timeout(self, temp_workspace):
        result = execute_shell(temp_workspace, "echo ok", timeout=10)
        assert result["success"]

    def test_execute_shell_timeout_exceeded(self, temp_workspace):
        # Use a command that sleeps longer than the timeout
        result = execute_shell(temp_workspace, "sleep 5", timeout=1)
        assert not result["success"]

    def test_execute_shell_with_cwd(self, temp_workspace):
        # Verify command runs in the workspace directory
        result = execute_shell(temp_workspace, "pwd")
        assert result["success"]
        # On Windows, pwd may use backslashes; normalize
        assert temp_workspace.resolve().name in result["stdout"].strip().replace("\\", "/")
