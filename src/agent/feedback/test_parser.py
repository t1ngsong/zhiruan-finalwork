import re
from agent.feedback import TestResult


class TestParser:
    @staticmethod
    def parse(stdout: str) -> TestResult | None:
        """解析 pytest 输出"""
        if not stdout.strip():
            return None

        # pytest 摘要行: "X passed, Y failed" 或 "X passed, Y failed, Z errors"
        passed = 0
        failed = 0
        errors = []

        # 匹配各种 pytest 摘要格式
        passed_match = re.search(r"(\d+)\s+passed", stdout)
        failed_match = re.search(r"(\d+)\s+failed", stdout)

        if passed_match:
            passed = int(passed_match.group(1))
        if failed_match:
            failed = int(failed_match.group(1))

        # 提取 FAILED 行
        for line in stdout.split("\n"):
            if "FAILED" in line and "::" in line:
                clean = line.replace("FAILED", "").strip()
                errors.append(clean)

        if passed == 0 and failed == 0 and not errors:
            return None

        return TestResult(passed=passed, failed=failed, errors=errors, raw_output=stdout)
