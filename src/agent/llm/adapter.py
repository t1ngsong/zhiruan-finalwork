# src/agent/llm/adapter.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict] | None = None
    finish_reason: str = "stop"
    usage: dict | None = None


class LLMAdapter(ABC):
    """LLM 适配器抽象——所有供应商实现此接口"""

    @abstractmethod
    def chat(self, messages: list[dict]) -> LLMResponse:
        """发送消息列表，返回 LLMResponse"""
        ...
