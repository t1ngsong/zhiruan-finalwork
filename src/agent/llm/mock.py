# src/agent/llm/mock.py
from agent.llm.adapter import LLMAdapter, LLMResponse


class MockLLMAdapter(LLMAdapter):
    """按预设脚本消费——用于确定性单元测试"""

    def __init__(self, script: list[LLMResponse]):
        self.script = script
        self.call_count = 0

    def chat(self, messages: list[dict]) -> LLMResponse:
        self.call_count += 1
        if self.call_count > len(self.script):
            return LLMResponse(content="", finish_reason="stop")
        return self.script[self.call_count - 1]
