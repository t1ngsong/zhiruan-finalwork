# src/agent/loop.py
from dataclasses import dataclass
from agent.config.loader import Config
from agent.llm.adapter import LLMAdapter
from agent.parser import ActionParser
from agent.tools.registry import ToolRegistry
from agent.tools.executor import ToolExecutor
from agent.guardrails.coordinator import GuardrailCoordinator
from agent.feedback.collector import FeedbackCollector
from agent.memory.store import MemoryStore
from agent.context import ContextBuilder
from agent.stop_checker import StopChecker


@dataclass
class AgentResult:
    success: bool
    summary: str
    rounds: int
    error: str | None = None


class AgentLoop:
    def __init__(
        self,
        config: Config,
        llm: LLMAdapter,
        parser: ActionParser,
        tool_registry: ToolRegistry,
        executor: ToolExecutor,
        guardrail: GuardrailCoordinator,
        feedback_collector: FeedbackCollector,
        memory: MemoryStore,
    ):
        self.config = config
        self.llm = llm
        self.parser = parser
        self.tool_registry = tool_registry
        self.executor = executor
        self.guardrail = guardrail
        self.feedback_collector = feedback_collector
        self.memory = memory
        self.context_builder = ContextBuilder(config, tool_registry, memory)
        self.stop_checker = StopChecker(config.max_rounds)

    def run(self, task: str) -> AgentResult:
        messages = [
            {"role": "system", "content": self.context_builder.build_system_prompt()},
            {"role": "user", "content": task},
        ]

        for round_num in range(1, self.config.max_rounds + 1):
            print(f"\n--- 第 {round_num} 轮 ---")

            # 1. 调用 LLM
            response = self.llm.chat(messages)

            # 2. 解析动作
            action = self.parser.parse(response)

            if action.type == "FINISH":
                print(f"Agent 完成: {action.content}")
                return AgentResult(success=True, summary=action.content, rounds=round_num)

            if action.type == "TEXT":
                print(f"Agent: {action.content[:100]}...")
                messages.append({"role": "assistant", "content": action.content})
                continue

            # 3. 工具调用 -> 护栏检查
            if action.type == "TOOL_CALL":
                print(f"工具调用: {action.tool_name}({action.args})")

                guard_result = self.guardrail.check(action.tool_name, action.args)
                if guard_result.blocked:
                    print(f"  🛡️ 护栏拦截: {guard_result.reason}")
                    feedback_text = f"[护栏拦截] {guard_result.reason}"
                    messages.append({"role": "tool", "content": feedback_text})
                    self.memory.record_decision(
                        f"{action.tool_name}({action.args})",
                        f"护栏拦截: {guard_result.reason}",
                        approved=False,
                    )
                    continue

                # 4. 执行工具
                result = self.executor.execute_tool(action.tool_name, action.args)
                print(f"  结果: {'成功' if result.success else '失败'} (exit={result.exit_code})")

                # 5. 收集反馈
                feedback = self.feedback_collector.collect(result)
                feedback_text = feedback.format_for_llm()

                # 6. 追加到消息
                messages.append({
                    "role": "assistant",
                    "content": f"[调用 {action.tool_name}({action.args})]",
                })
                messages.append({"role": "tool", "content": feedback_text})

                # 7. 记忆写入
                self.memory.record_decision(
                    f"{action.tool_name}({action.args})",
                    feedback_text,
                    approved=True,
                )

                # 8. 停机判断
                should_stop, reason = self.stop_checker.should_stop(feedback, round_num)
                if should_stop:
                    success = feedback.success and (
                        not feedback.test_result or feedback.test_result.failed == 0
                    )
                    return AgentResult(success=success, summary=reason, rounds=round_num)

        return AgentResult(success=False, summary=f"超过最大轮数 ({self.config.max_rounds})", rounds=round_num)
