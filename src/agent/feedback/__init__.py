from dataclasses import dataclass, field


@dataclass
class TestResult:
    passed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    raw_output: str = ""


@dataclass
class LintIssue:
    file: str = ""
    line: int = 0
    message: str = ""


@dataclass
class TypeErrorInfo:
    file: str = ""
    line: int = 0
    message: str = ""


@dataclass
class Feedback:
    exit_code: int = 0
    success: bool = True
    test_result: TestResult | None = None
    lint_issues: list[LintIssue] = field(default_factory=list)
    type_errors: list[TypeErrorInfo] = field(default_factory=list)

    def format_for_llm(self) -> str:
        parts = []
        if self.test_result:
            parts.append(f"[测试] {self.test_result.passed} 通过, {self.test_result.failed} 失败")
            for err in self.test_result.errors[:5]:
                parts.append(f"  ❌ {err}")
        if self.lint_issues:
            parts.append(f"[Lint] {len(self.lint_issues)} 个问题")
            for issue in self.lint_issues[:3]:
                parts.append(f"  ⚠️ {issue.file}:{issue.line} - {issue.message}")
        if self.type_errors:
            parts.append(f"[类型检查] {len(self.type_errors)} 个错误")
            for err in self.type_errors[:3]:
                parts.append(f"  🔴 {err.file}:{err.line} - {err.message}")
        if not self.success:
            parts.append(f"[退出码] {self.exit_code}")
        return "\n".join(parts) if parts else "✅ 全部通过"
