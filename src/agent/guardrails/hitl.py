"""Human-In-The-Loop approval gate with state machine and real timeout."""

import threading
from agent.guardrails import RiskResult
from agent.tools import RiskLevel


class HITLGate:
    """State machine for human-in-the-loop approval.

    States: IDLE -> WAITING -> (APPROVED/REJECTED/TIMEOUT) -> IDLE

    The terminal state persists after request_approval returns so that
    callers and tests can observe it. State resets to IDLE at the
    beginning of the next call.

    - FATAL: auto-reject, state goes IDLE -> REJECTED
    - LOW: auto-approve, state goes IDLE -> APPROVED
    - MEDIUM/HIGH: prompt user via stdin with real timeout
    """

    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.state = "IDLE"

    def request_approval(self, tool_name: str, args: dict, risk: RiskResult) -> bool:
        # Reset to IDLE at the start of each request
        self.state = "IDLE"

        # FATAL is always rejected
        if risk.level == RiskLevel.FATAL:
            self.state = "REJECTED"
            return False

        # LOW is always approved
        if risk.level == RiskLevel.LOW:
            self.state = "APPROVED"
            return True

        # MEDIUM / HIGH: human decision required with real timeout
        self.state = "WAITING"

        print(f"\n  ⚠️  风险等级: {risk.level.value}")
        print(f"  动作: {tool_name} {args}")
        print(f"  原因: {risk.reason}")

        user_input = [None]
        input_event = threading.Event()

        def reader():
            try:
                user_input[0] = input(
                    f"  批准执行? [y/N] ({self.timeout}s 超时自动拒绝): "
                )
            except Exception:
                # Any failure to read input (EOFError, KeyboardInterrupt,
                # OSError from pytest capture, etc.) means no user input
                user_input[0] = None
            finally:
                input_event.set()

        t = threading.Thread(target=reader, daemon=True)
        t.start()

        finished = input_event.wait(timeout=self.timeout)

        if not finished:
            self.state = "TIMEOUT"
            return False

        answer = user_input[0]
        if answer and answer.lower() == "y":
            self.state = "APPROVED"
            return True
        else:
            self.state = "REJECTED"
            return False
