# tests/llm/test_mock.py
import pytest
from agent.llm.adapter import LLMAdapter, LLMResponse


def test_llm_adapter_is_abstract():
    """LLMAdapter 不能直接实例化"""
    with pytest.raises(TypeError):
        LLMAdapter()


def test_mock_llm_returns_scripted_responses():
    """MockLLMAdapter 按预设序列返回响应"""
    from agent.llm.mock import MockLLMAdapter

    script = [
        LLMResponse(content="hello", finish_reason="stop"),
        LLMResponse(content="world", finish_reason="stop"),
    ]
    llm = MockLLMAdapter(script)

    r1 = llm.chat([{"role": "user", "content": "hi"}])
    assert r1.content == "hello"
    assert r1.finish_reason == "stop"

    r2 = llm.chat([{"role": "user", "content": "again"}])
    assert r2.content == "world"


def test_mock_llm_returns_finish_when_script_exhausted():
    """脚本耗尽时返回 FINISH"""
    from agent.llm.mock import MockLLMAdapter

    llm = MockLLMAdapter([])
    r = llm.chat([{"role": "user", "content": "hi"}])
    assert r.finish_reason == "stop"


def test_mock_llm_call_count():
    """验证 call_count 正确递增"""
    from agent.llm.mock import MockLLMAdapter

    llm = MockLLMAdapter([
        LLMResponse(content="a", finish_reason="stop"),
    ])
    assert llm.call_count == 0
    llm.chat([])
    assert llm.call_count == 1
    llm.chat([])
    assert llm.call_count == 2


def test_mock_llm_with_tool_calls():
    """MockLLMAdapter 支持返回 tool_calls"""
    from agent.llm.mock import MockLLMAdapter

    script = [
        LLMResponse(
            content="",
            tool_calls=[{"name": "shell", "arguments": '{"cmd": "pytest"}'}],
            finish_reason="tool_calls",
        ),
    ]
    llm = MockLLMAdapter(script)
    r = llm.chat([])
    assert r.tool_calls is not None
    assert r.tool_calls[0]["name"] == "shell"
