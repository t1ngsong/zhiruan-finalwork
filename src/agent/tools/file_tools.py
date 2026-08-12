"""File tools: read_file and write_file with workspace confinement."""

from pathlib import Path


def read_file(workspace: Path, path: str) -> str:
    """Read the contents of a file within the workspace.

    Args:
        workspace: Root directory that confines file access.
        path: Relative path to the file within the workspace.

    Returns:
        The file contents as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    file_path = (workspace / path).resolve()

    # Security: ensure the resolved path is within the workspace
    # Using is_relative_to (Python 3.9+) to prevent prefix-collision bypasses
    if not file_path.is_relative_to(workspace.resolve()):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return file_path.read_text(encoding="utf-8")


def write_file(workspace: Path, path: str, content: str) -> str:
    """Write content to a file within the workspace (overwrites if exists).

    Args:
        workspace: Root directory that confines file access.
        path: Relative path to the file within the workspace.
        content: Text content to write.

    Returns:
        Confirmation message.
    """
    file_path = (workspace / path).resolve()

    # Security: ensure the resolved path is within the workspace
    # Using is_relative_to (Python 3.9+) to prevent prefix-collision bypasses
    if not file_path.is_relative_to(workspace.resolve()):
        raise ValueError(f"Path outside workspace: {path}")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"Written to {file_path}"
