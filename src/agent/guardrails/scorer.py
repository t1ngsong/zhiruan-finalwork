"""Risk scorer that evaluates tool calls against patterns and workspace."""

from pathlib import Path
from agent.tools import RiskLevel
from agent.guardrails.patterns import match_pattern
from agent.guardrails import RiskResult


class RiskScorer:
    """Scores tool calls by risk level.

    - read_file / search: always LOW
    - write_file: FATAL if target is outside workspace
    - shell: pattern-matched against dangerous commands
    """

    def __init__(self, workspace: Path, custom_patterns: list[dict] = None):
        self.workspace = Path(workspace).resolve()
        self.custom_patterns = custom_patterns or []

    def score(self, tool_name: str, args: dict) -> RiskResult:
        # Search and read: always low risk
        if tool_name in ("read_file", "search"):
            return RiskResult(RiskLevel.LOW, "")

        # Write: check that target is inside workspace
        if tool_name == "write_file":
            target = self.workspace / args.get("path", "")
            try:
                if not target.resolve().is_relative_to(self.workspace):
                    return RiskResult(RiskLevel.FATAL, f"写入路径超出工作区: {args.get('path')}")
            except (ValueError, OSError):
                return RiskResult(RiskLevel.FATAL, f"无效路径: {args.get('path')}")
            return RiskResult(RiskLevel.LOW, "")

        # Shell: pattern matching
        if tool_name == "shell":
            cmd = args.get("cmd", "")
            return match_pattern(cmd, self.custom_patterns)

        return RiskResult(RiskLevel.LOW, "")
