import re
from agent.feedback import LintIssue


class LintParser:
    @staticmethod
    def parse(stdout: str) -> list[LintIssue]:
        """解析 ruff/flake8 输出格式: file:line:col: CODE message"""
        issues = []
        for line in stdout.split("\n"):
            # ruff 格式: file:line:col: CODE message
            match = re.match(r"^(.+?):(\d+):\d+:\s+(\w+)\s+(.+)$", line.strip())
            if match:
                issues.append(LintIssue(
                    file=match.group(1),
                    line=int(match.group(2)),
                    message=f"{match.group(3)}: {match.group(4)}",
                ))
                continue
            # flake8 格式: file:line:col: CODE message
            match = re.match(r"^(.+?):(\d+):\d+:\s+(\w\d+)\s+(.+)$", line.strip())
            if match:
                issues.append(LintIssue(
                    file=match.group(1),
                    line=int(match.group(2)),
                    message=f"{match.group(3)}: {match.group(4)}",
                ))
        return issues
