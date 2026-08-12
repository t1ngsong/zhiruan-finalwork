from agent.feedback.type_parser import TypeCheckParser


def test_parse_mypy_error():
    stdout = 'src/main.py:10: error: Incompatible types in assignment'
    errors = TypeCheckParser.parse(stdout)
    assert len(errors) == 1
    assert errors[0].file == "src/main.py"
    assert errors[0].line == 10


def test_parse_empty():
    assert TypeCheckParser.parse("") == []
