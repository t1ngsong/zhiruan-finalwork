# tests/test_parser.py
import pytest
from agent.llm.adapter import LLMResponse
from agent.parser import ActionParser, Action


def test_parse_finish():
    """解析 FINISH 类型响应"""
    parser = ActionParser()
    response = LLMResponse(content="任务完成", finish_reason="stop")
    action = parser.parse(response)
    assert action.type == "FINISH"
    assert action.content == "任务完成"


def test_parse_text_response():
    """解析纯文本响应（不是工具调用，是来自 LLM 的自然语言消息）"""
    parser = ActionParser()
    response = LLMResponse(
        content="我需要先读取文件来理解问题",
        finish_reason="stop",
    )
    action = parser.parse(response)
    assert action.type == "TEXT"
    assert action.content == "我需要先读取文件来理解问题"


def test_parse_tool_call():
    """解析工具调用响应"""
    parser = ActionParser()
    response = LLMResponse(
        content="",
        tool_calls=[{
            "name": "shell",
            "arguments": '{"cmd": "pytest tests/"}',
        }],
        finish_reason="tool_calls",
    )
    action = parser.parse(response)
    assert action.type == "TOOL_CALL"
    assert action.tool_name == "shell"
    assert action.args == {"cmd": "pytest tests/"}


def test_parse_tool_call_with_json_parse_error():
    """工具调用参数 JSON 解析失败时返回错误 Action"""
    parser = ActionParser()
    response = LLMResponse(
        content="",
        tool_calls=[{
            "name": "shell",
            "arguments": '{invalid json',
        }],
        finish_reason="tool_calls",
    )
    action = parser.parse(response)
    assert action.type == "TEXT"
    assert "参数解析失败" in action.content
