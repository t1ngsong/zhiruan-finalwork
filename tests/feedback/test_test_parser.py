from agent.feedback.test_parser import TestParser


def test_parse_pytest_summary():
    stdout = """
tests/test_x.py::test_a PASSED
tests/test_x.py::test_b FAILED
======= 1 passed, 1 failed in 0.5s =======
"""
    result = TestParser.parse(stdout)
    assert result is not None
    assert result.passed == 1
    assert result.failed == 1


def test_parse_all_pass():
    stdout = "======= 5 passed in 0.5s ======="
    result = TestParser.parse(stdout)
    assert result.passed == 5
    assert result.failed == 0


def test_parse_empty_returns_none():
    assert TestParser.parse("") is None
