# src/agent/parser.py
import json
from dataclasses import dataclass, field
from agent.llm.adapter import LLMResponse


@dataclass
class Action:
    type: str              # "TEXT" | "TOOL_CALL" | "FINISH"
    content: str = ""
    tool_name: str = ""
    args: dict = field(default_factory=dict)
    tool_call_id: str = ""


class ActionParser:
    """解析 LLM 响应为结构化 Action"""

    def parse(self, response: LLMResponse) -> Action:
        # 工具调用
        if response.tool_calls:
            tc = response.tool_calls[0]
            tool_name = tc.get("name", "")
            args_str = tc.get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError as e:
                return Action(
                    type="TEXT",
                    content=f"[错误] 工具调用参数解析失败: {e}\n原始参数: {args_str}",
                )
            return Action(
                type="TOOL_CALL",
                tool_name=tool_name,
                args=args,
                tool_call_id=tc.get("id", ""),
            )

        # 纯文本（判断是否为 FINISH）
        content = response.content.strip() if response.content else ""
        content_upper = content.upper()
        # 综合启发式：检测 FINISH 关键词（英文或中文）
        finish_indicators = ["FINISH", "完成", "DONE", "COMPLETE"]
        if any(indicator.upper() in content_upper[:30] for indicator in finish_indicators):
            return Action(type="FINISH", content=content)

        return Action(type="TEXT", content=content)
