# tests/test_stop_checker.py
from agent.stop_checker import StopChecker
from agent.feedback import Feedback, TestResult


def test_stop_on_max_rounds():
    checker = StopChecker(max_rounds=3)
    should, reason = checker.should_stop(None, 3, None)
    assert should
    assert "最大轮数" in reason


def test_continue_before_max():
    checker = StopChecker(max_rounds=3)
    should, reason = checker.should_stop(None, 2, None)
    assert not should


def test_stop_on_all_pass():
    checker = StopChecker(max_rounds=10)
    fb = Feedback(test_result=TestResult(passed=3, failed=0))
    should, reason = checker.should_stop(fb, 1, None)
    assert should


def test_continue_on_failure():
    checker = StopChecker(max_rounds=10)
    fb = Feedback(test_result=TestResult(passed=2, failed=1))
    should, reason = checker.should_stop(fb, 1, None)
    assert not should


def test_stop_on_finish_action():
    checker = StopChecker(max_rounds=10)
    should, reason = checker.should_stop(None, 1, "FINISH")
    assert should
    assert "主动完成" in reason
