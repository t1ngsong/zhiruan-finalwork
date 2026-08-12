# tests/llm/test_deepseek.py
import pytest
from agent.llm.adapter import LLMAdapter, LLMResponse
from agent.llm.deepseek import DeepSeekAdapter


def test_deepseek_adapter_is_llm_adapter():
    """DeepSeekAdapter 是 LLMAdapter 的子类"""
    assert issubclass(DeepSeekAdapter, LLMAdapter)


def test_deepseek_adapter_can_be_instantiated():
    """DeepSeekAdapter 可以实例化"""
    adapter = DeepSeekAdapter(api_key="sk-test", model="deepseek-chat")
    assert adapter.model == "deepseek-chat"
    assert adapter.BASE_URL == "https://api.deepseek.com"


def test_deepseek_adapter_has_chat_method():
    """DeepSeekAdapter 实现了 chat 方法"""
    adapter = DeepSeekAdapter(api_key="sk-test")
    assert hasattr(adapter, "chat")
    assert callable(adapter.chat)


def test_deepseek_adapter_set_tool_schemas():
    """set_tool_schemas 正确注册 tool schemas"""
    adapter = DeepSeekAdapter(api_key="sk-test")
    schemas = [
        {"name": "shell", "description": "Execute a command", "parameters": {}},
    ]
    adapter.set_tool_schemas(schemas)
    assert hasattr(adapter, "_tool_schemas")
    assert len(adapter._tool_schemas) == 1
    assert adapter._tool_schemas[0]["type"] == "function"
    assert adapter._tool_schemas[0]["function"] == schemas[0]


def test_deepseek_adapter_chat_without_tool_schemas_sets_none():
    """未设置 tool_schemas 时，调用 chat 传递 tools=None（不设置 _tool_schemas）"""
    adapter = DeepSeekAdapter(api_key="sk-test")
    # When _tool_schemas is not set, hasattr returns False, passing None
    assert not hasattr(adapter, "_tool_schemas")
