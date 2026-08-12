"""Search tool: grep-based search with Python fallback."""

import subprocess
from pathlib import Path


def search(workspace: Path, pattern: str, path: str = ".") -> str:
    """Search for a pattern in Python files within the workspace.

    Uses grep if available, with a pure-Python fallback.

    Args:
        workspace: Root directory to search within.
        pattern: The text pattern to search for.
        path: Subdirectory relative to workspace (default "." for all).

    Returns:
        Matching lines with file:line:content format, or "No matches found".
    """
    search_path = (workspace / path).resolve()

    # Security: ensure the search path is within the workspace
    # Using is_relative_to (Python 3.9+) to prevent prefix-collision bypasses
    if not search_path.is_relative_to(workspace.resolve()):
        return "No matches found"

    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", pattern, str(search_path)],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout or "No matches found"
    except FileNotFoundError:
        # grep not available -- fall back to Python
        return _python_search(search_path, pattern)


def _python_search(search_path: Path, pattern: str) -> str:
    """Pure-Python fallback search for pattern in .py files."""
    matches: list[str] = []
    for py_file in search_path.rglob("*.py"):
        try:
            lines = py_file.read_text(encoding="utf-8").split("\n")
            for i, line in enumerate(lines, 1):
                if pattern in line:
                    matches.append(f"{py_file}:{i}:{line.strip()}")
        except Exception:
            pass
    return "\n".join(matches) if matches else "No matches found"
