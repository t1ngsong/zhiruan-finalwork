# src/agent/stop_checker.py
from agent.feedback import Feedback


class StopChecker:
    def __init__(self, max_rounds: int = 20):
        self.max_rounds = max_rounds

    def should_stop(self, feedback: Feedback | None, round_num: int,
                    action_type: str | None = None) -> tuple[bool, str]:
        if round_num >= self.max_rounds:
            return True, f"达到最大轮数 ({self.max_rounds})"

        if action_type == "FINISH":
            return True, "Agent 主动完成"

        if feedback and feedback.test_result:
            if feedback.test_result.failed == 0 and not feedback.lint_issues and not feedback.type_errors:
                return True, "所有测试通过，无 lint/类型错误"

        return False, ""
