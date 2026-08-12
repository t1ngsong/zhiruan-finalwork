"""Shell tool: execute shell commands within the workspace."""

import subprocess
import os
from pathlib import Path


def execute_shell(workspace: Path, cmd: str, timeout: int = 30) -> dict:
    """Execute a shell command within the workspace directory.

    Args:
        workspace: The directory in which to run the command.
        cmd: The shell command string to execute.
        timeout: Maximum time in seconds before the command is killed.

    Returns:
        A dict with keys: success, exit_code, stdout, stderr.
    """
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=str(workspace), timeout=timeout,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "success": False,
        }
