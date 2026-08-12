# src/agent/context.py
import json
from agent.config.loader import Config
from agent.tools.registry import ToolRegistry
from agent.memory.store import MemoryStore


class ContextBuilder:
    def __init__(self, config: Config, tool_registry: ToolRegistry, memory: MemoryStore):
        self.config = config
        self.tool_registry = tool_registry
        self.memory = memory

    def build_system_prompt(self) -> str:
        tools_schema = json.dumps(
            self.tool_registry.get_schemas_for_llm(), ensure_ascii=False
        )
        rules = self.memory.get_rules()
        recent = self.memory.get_recent_decisions(5)
        decisions_text = ""
        if recent:
            decisions_text = "\n最近决策:\n" + "\n".join(
                f"- {d['action_summary']} -> {d['result_summary']}"
                for d in recent
            )

        return f"""你是一个 Coding Agent，负责完成用户指定的编码任务。

你可以使用以下工具：
{tools_schema}

项目约定：
{rules or "（暂无项目约定）"}
{decisions_text}

规则：
1. 每次只能调用一个工具
2. 完成任务后回复 FINISH
3. 如果工具执行后的反馈显示测试失败、lint 错误或类型错误，请修复代码后重新运行验证
4. 所有文件路径使用相对路径"""
