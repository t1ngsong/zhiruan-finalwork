"""Dangerous command pattern matching library."""

import re
from agent.tools import RiskLevel
from agent.guardrails import RiskResult

DANGEROUS_PATTERNS: list[tuple[str, RiskLevel, str]] = [
    # Only FATAL for rm -rf / (root), rm -rf /* (glob root), or
    # rm -rf /path/to (with trailing space/end indicating no further args).
    # rm -rf /tmp, rm -rf /home/user, etc. are NOT caught here
    # (they will still be caught by ScopeFence if absolute paths are used).
    (r"rm\s+(-r\w*\s*|-rf\s*|--recursive\s+)/(\s|$|\*)", RiskLevel.FATAL, "递归删除根目录"),
    (r"\bDROP\s+(TABLE|DATABASE)\b",                  RiskLevel.FATAL,  "删除数据库"),
    (r">\s*/dev/sd[a-z]",                             RiskLevel.FATAL,  "覆写磁盘设备"),
    (r"\bchmod\s+777\b",                              RiskLevel.HIGH,   "权限过度开放"),
    (r"\bgit\s+push\s+--force\b",                     RiskLevel.HIGH,   "强制推送"),
    (r"\bcurl.*\|\s*(ba)?sh\b",                       RiskLevel.HIGH,   "管道执行远程脚本"),
    (r"\b(sudo|su)\b",                                RiskLevel.MEDIUM, "提权操作"),
    (r"\bpip\s+install\b",                            RiskLevel.MEDIUM, "安装Python包"),
]


def match_pattern(cmd: str, custom_patterns: list[dict] = None) -> RiskResult:
    """Match a shell command against dangerous patterns.

    Checks custom patterns first, then the built-in DANGEROUS_PATTERNS.
    Returns the first match found, or RiskLevel.LOW if no match.
    """
    # Check custom patterns first (user overrides)
    if custom_patterns:
        for cp in custom_patterns:
            pat = cp.get("pattern", "")
            level_str = cp.get("level", "LOW")
            reason = cp.get("reason", "")
            try:
                if pat and re.search(pat, cmd):
                    return RiskResult(RiskLevel(level_str), reason)
            except re.error:
                continue

    # Check default patterns
    for pattern, level, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd):
            return RiskResult(level, reason)

    return RiskResult(RiskLevel.LOW, "")
