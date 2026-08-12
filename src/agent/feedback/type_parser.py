import re
from agent.feedback import TypeErrorInfo


class TypeCheckParser:
    @staticmethod
    def parse(stdout: str) -> list[TypeErrorInfo]:
        """解析 mypy 输出格式: file:line: error: message"""
        errors = []
        for line in stdout.split("\n"):
            match = re.match(r"^(.+?):(\d+):\s+error:\s+(.+)$", line.strip())
            if match:
                errors.append(TypeErrorInfo(
                    file=match.group(1),
                    line=int(match.group(2)),
                    message=match.group(3),
                ))
        return errors
