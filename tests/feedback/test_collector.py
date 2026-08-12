from agent.tools import ToolResult
from agent.feedback.collector import FeedbackCollector


def test_collect_success_with_test_results():
    collector = FeedbackCollector()
    result = ToolResult(
        success=True, exit_code=0,
        stdout="3 passed in 0.5s",
        tool_name="shell",
    )
    fb = collector.collect(result)
    assert fb.success
    assert fb.test_result.passed == 3


def test_collect_failure():
    collector = FeedbackCollector()
    result = ToolResult(success=False, exit_code=1, stderr="error", tool_name="shell")
    fb = collector.collect(result)
    assert not fb.success
    assert fb.exit_code == 1


def test_format_for_llm():
    from agent.feedback import Feedback, TestResult, LintIssue, TypeErrorInfo
    fb = Feedback(
        success=False,
        exit_code=1,
        test_result=TestResult(passed=2, failed=1, errors=["FAILED test_x"]),
        lint_issues=[LintIssue(file="x.py", line=10, message="F841: unused")],
        type_errors=[TypeErrorInfo(file="y.py", line=5, message="Incompatible types")],
    )
    text = fb.format_for_llm()
    assert "测试" in text
    assert "Lint" in text
    assert "类型检查" in text
    assert "FAILED test_x" in text
