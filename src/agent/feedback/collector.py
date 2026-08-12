from agent.tools import ToolResult
from agent.feedback import Feedback
from agent.feedback.test_parser import TestParser
from agent.feedback.lint_parser import LintParser
from agent.feedback.type_parser import TypeCheckParser


class FeedbackCollector:
    def __init__(self):
        self.test_parser = TestParser()
        self.lint_parser = LintParser()
        self.type_parser = TypeCheckParser()

    def collect(self, result: ToolResult) -> Feedback:
        fb = Feedback(
            exit_code=result.exit_code,
            success=result.success,
        )

        if not result.success:
            fb.test_result = None
            return fb

        stdout = result.stdout

        # 尝试解析测试结果
        test_result = self.test_parser.parse(stdout)
        if test_result:
            fb.test_result = test_result

        # 尝试解析 lint 输出
        lint_issues = self.lint_parser.parse(stdout)
        if lint_issues:
            fb.lint_issues = lint_issues

        # 尝试解析类型检查输出
        type_errors = self.type_parser.parse(stdout)
        if type_errors:
            fb.type_errors = type_errors

        return fb
