"""Shared pytest fixtures for the coding agent harness."""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_workspace):
    """Create a sample Python file in the workspace."""
    file_path = temp_workspace / "hello.py"
    file_path.write_text("def hello():\n    return 'Hello, World!'\n")
    return file_path
