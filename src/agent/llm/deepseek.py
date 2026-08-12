# src/agent/llm/deepseek.py
from openai import OpenAI
from agent.llm.adapter import LLMAdapter, LLMResponse


class DeepSeekAdapter(LLMAdapter):
    """对接 DeepSeek Chat API（兼容 OpenAI 接口）"""

    BASE_URL = "https://api.deepseek.com"

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.client = OpenAI(api_key=api_key, base_url=self.BASE_URL)
        self.model = model

    def chat(self, messages: list[dict]) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self._tool_schemas if hasattr(self, "_tool_schemas") else None,
        )
        choice = response.choices[0]
        msg = choice.message

        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                    "id": tc.id,
                }
                for tc in msg.tool_calls
            ]

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            } if response.usage else None,
        )

    def set_tool_schemas(self, schemas: list[dict]):
        """注册工具 schemas 供 LLM function calling 使用"""
        self._tool_schemas = [
            {"type": "function", "function": s} for s in schemas
        ]
