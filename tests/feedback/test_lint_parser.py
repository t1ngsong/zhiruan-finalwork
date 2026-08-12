from agent.feedback.lint_parser import LintParser


def test_parse_ruff_output():
    stdout = "src/main.py:10:5: F841 unused variable x"
    issues = LintParser.parse(stdout)
    assert len(issues) == 1
    assert issues[0].file == "src/main.py"
    assert issues[0].line == 10
    assert "F841" in issues[0].message


def test_parse_empty():
    assert LintParser.parse("") == []
