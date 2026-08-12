"""Tests for search_tool (search)."""

import pytest
from agent.tools.search_tool import search


class TestSearch:
    def test_search_finds_pattern(self, temp_workspace, sample_file):
        result = search(temp_workspace, "hello", ".")
        assert "hello" in result.lower()

    def test_search_no_match(self, temp_workspace, sample_file):
        result = search(temp_workspace, "nonexistent_pattern_xyz", ".")
        assert result == "No matches found" or result == "无匹配结果"

    def test_search_in_subdirectory(self, temp_workspace):
        subdir = temp_workspace / "sub"
        subdir.mkdir()
        f = subdir / "test.py"
        f.write_text("x = 42\n")
        result = search(temp_workspace, "42", "sub")
        assert "42" in result

    def test_search_default_path(self, temp_workspace, sample_file):
        result = search(temp_workspace, "hello")
        assert "hello" in result.lower()

    def test_search_respects_py_files_only(self, temp_workspace):
        # Create a .txt file that should NOT be searched
        txt_file = temp_workspace / "notes.txt"
        txt_file.write_text("hello world\n")
        # Create a .py file that should be searched
        py_file = temp_workspace / "script.py"
        py_file.write_text("hello world\n")
        result = search(temp_workspace, "hello")
        # Should find the .py file match
        assert "script.py" in result
        # Should NOT find the .txt file
        assert "notes.txt" not in result

    def test_rejects_path_traversal_dot_dot(self, temp_workspace):
        """search must reject ../ escape attempts."""
        result = search(temp_workspace, "hello", "..")
        assert result == "No matches found"

    def test_rejects_path_traversal_prefix_collision(self, temp_workspace):
        """search must reject prefix-collision bypass."""
        ws_parent = temp_workspace.parent
        evil_dir = ws_parent / (temp_workspace.name + "_evil")
        evil_dir.mkdir(exist_ok=True)
        try:
            result = search(
                temp_workspace,
                "hello",
                f"../{temp_workspace.name}_evil",
            )
            assert result == "No matches found"
        finally:
            evil_dir.rmdir()

    def test_rejects_absolute_path(self, temp_workspace):
        """search must reject absolute paths pointing outside workspace."""
        result = search(temp_workspace, "hello", "/etc")
        assert result == "No matches found"
