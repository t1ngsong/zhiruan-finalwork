"""Tests for file_tools (read_file, write_file)."""

import pytest
from agent.tools.file_tools import read_file, write_file


class TestReadFile:
    def test_read_file(self, temp_workspace, sample_file):
        content = read_file(temp_workspace, "hello.py")
        assert "def hello()" in content

    def test_read_file_not_found(self, temp_workspace):
        with pytest.raises(FileNotFoundError, match="File not found"):
            read_file(temp_workspace, "nonexistent.py")

    def test_read_file_empty(self, temp_workspace):
        f = temp_workspace / "empty.txt"
        f.write_text("")
        content = read_file(temp_workspace, "empty.txt")
        assert content == ""

    def test_read_file_with_unicode(self, temp_workspace):
        f = temp_workspace / "unicode.txt"
        f.write_text("Hello, 世界!\n", encoding="utf-8")
        content = read_file(temp_workspace, "unicode.txt")
        assert "世界" in content

    def test_rejects_path_traversal_dot_dot(self, temp_workspace):
        """read_file must reject ../ escape attempts."""
        with pytest.raises(FileNotFoundError):
            read_file(temp_workspace, "../outside_file.txt")

    def test_rejects_path_traversal_prefix_collision(self, temp_workspace):
        """read_file must reject prefix-collision bypass (e.g. workspace /tmp/ws
        allowing /tmp/wsfoo via ../wsfoo/evil)."""
        # Create a sibling directory whose name starts with workspace name
        ws_parent = temp_workspace.parent
        evil_dir = ws_parent / (temp_workspace.name + "_evil")
        evil_dir.mkdir(exist_ok=True)
        evil_file = evil_dir / "secret.txt"
        evil_file.write_text("evil")
        try:
            with pytest.raises(FileNotFoundError):
                read_file(temp_workspace, f"../{temp_workspace.name}_evil/secret.txt")
        finally:
            # Clean up
            evil_file.unlink(missing_ok=True)
            evil_dir.rmdir()

    def test_rejects_absolute_path(self, temp_workspace):
        """read_file must reject absolute paths pointing outside workspace."""
        with pytest.raises(FileNotFoundError):
            read_file(temp_workspace, "/etc/passwd")


class TestWriteFile:
    def test_write_file(self, temp_workspace):
        result = write_file(temp_workspace, "new.py", "x = 1")
        assert (temp_workspace / "new.py").read_text() == "x = 1"
        assert "Written to" in result or "已写入" in result

    def test_write_file_creates_parent_dirs(self, temp_workspace):
        result = write_file(temp_workspace, "sub/dir/file.py", "x = 1")
        assert (temp_workspace / "sub" / "dir" / "file.py").read_text() == "x = 1"

    def test_write_file_overwrites_existing(self, temp_workspace):
        f = temp_workspace / "existing.py"
        f.write_text("old content")
        result = write_file(temp_workspace, "existing.py", "new content")
        assert f.read_text() == "new content"

    def test_write_file_empty_content(self, temp_workspace):
        result = write_file(temp_workspace, "empty.py", "")
        assert (temp_workspace / "empty.py").read_text() == ""

    def test_rejects_write_path_traversal_dot_dot(self, temp_workspace):
        """write_file must reject ../ escape attempts."""
        with pytest.raises(ValueError, match="outside workspace"):
            write_file(temp_workspace, "../outside_file.txt", "data")

    def test_rejects_write_path_traversal_prefix_collision(self, temp_workspace):
        """write_file must reject prefix-collision bypass."""
        ws_parent = temp_workspace.parent
        evil_dir = ws_parent / (temp_workspace.name + "_evil")
        evil_dir.mkdir(exist_ok=True)
        try:
            with pytest.raises(ValueError, match="outside workspace"):
                write_file(
                    temp_workspace,
                    f"../{temp_workspace.name}_evil/secret.txt",
                    "evil",
                )
        finally:
            evil_dir.rmdir()

    def test_rejects_write_absolute_path(self, temp_workspace):
        """write_file must reject absolute paths pointing outside workspace."""
        with pytest.raises(ValueError, match="outside workspace"):
            write_file(temp_workspace, "/etc/malicious", "data")
