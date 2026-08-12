# SPEC.md — Coding Agent Harness

> AI4SE 期末项目 · A 方向 · Coding Agent Harness

---

## 1. 问题陈述

### 1.1 要解决什么问题？

当前市面上的 Coding Agent（如 Claude Code、Cursor、GitHub Copilot Chat）虽然功能强大，但其核心机制——主循环、工具分发、护栏拦截、反馈闭环——对用户来说是**黑盒**。用户无法理解 Agent 为什么做出某个决策，也无法定制其治理行为。

本项目的目标是：**从零构建一个透明、可定制、可独立验证的 Coding Agent Harness**，证明 Agent 的核心价值不只在 LLM 的"智能"，更在 Harness 层的工程机制。

### 1.2 目标用户

- **软件工程学习者**：通过阅读和运行这个 Harness，理解 Agent = LLM + Harness 的本质
- **对 Agent 安全有要求的开发者**：需要可审计的护栏机制，而非"信任 LLM 的自律"

### 1.3 为什么值得做？

课程的核心命题是"当 LLM 能完成大部分编码工作时，工程师的价值在哪里"。本项目用代码回答了这个问题：**工程师的价值落在 Harness 这层工程上**——治理、反馈、上下文、安全、分发。这些机制必须由代码实现，不能靠提示词代替。

---

## 2. 用户故事

按 INVEST 原则编写。

| # | 用户故事 | 验收条件 |
|---|---------|---------|
| US1 | 作为一个开发者，我可以通过 CLI 向 Agent 下达一个编码任务（如"修复 auth.py 中的 bug"），Agent 自主完成多轮工具调用直到任务完成或超时 | Agent 接收任务后进入主循环，调用 LLM → 解析动作 → 执行工具 → 收集反馈 → 自动判断停机 |
| US2 | 作为一个开发者，当 Agent 尝试执行危险命令（如 `rm -rf /`）时，系统能自动拦截并告知我原因 | 护栏识别危险模式后阻止执行，向用户展示风险原因，记录拦截日志 |
| US3 | 作为一个开发者，当 Agent 执行了中等风险操作（如 `git push --force`）时，系统暂停并等待我的人工审批 | HITL 状态机进入 WAITING 状态，用户在 60 秒内输入 y/N 决定批准或拒绝 |
| US4 | 作为一个开发者，Agent 每次执行 Shell 命令后，我能看到客观的反馈信号（测试通过/失败、lint 问题数、类型错误），Agent 据此自动修正 | 反馈收集器解析 stdout/stderr，结构化呈现，LLM 在下一轮依据反馈调整行为 |
| US5 | 作为一个开发者，我可以通过 `.agent.yaml` 配置文件自定义危险命令规则、工具白名单、最大轮数等 | 配置文件在启动时加载，覆盖默认值，CLI 参数可进一步覆盖配置文件 |
| US6 | 作为一个开发者，我可以用 Mock LLM 替换真实 LLM，在离线环境下确定性地测试 Harness 的所有核心机制 | 注入 MockLLMAdapter 后，`pytest` 全量通过且不访问网络 |
| US7 | 作为一个新用户，我可以通过 `docker build && docker run` 一键启动 Agent，并在首次运行时安全地录入我的 DeepSeek API Key | Docker 镜像构建成功，首次运行引导用户输入 key（不回显），key 存储在容器内的加密文件中 |

---

## 3. 功能规约

### 3.1 Agent 主循环

| 属性 | 描述 |
|------|------|
| **输入** | 用户任务描述（自然语言字符串） |
| **行为** | 见下方伪代码流程 |
| **输出** | `AgentResult(success, summary, rounds)` |
| **边界条件** | 最大轮数达到上限 → 返回失败；LLM 返回 `FINISH` → 提前退出 |
| **错误处理** | LLM 调用失败 → 重试最多 3 次 → 仍失败则终止；工具执行超时 → 记录超时反馈继续下一轮 |

**流程**：
1. 上下文组装（系统提示 + 配置规则 + 对话历史 + 记忆）
2. 调用 LLM（通过 LLMAdapter 抽象接口）
3. 解析 LLM 响应为 Action（TEXT / TOOL_CALL / FINISH）
4. **护栏检查**（见 §3.3）
5. 工具分发与执行（见 §3.2）
6. 反馈收集（见 §3.4）
7. 记忆写入
8. 停机判断 → 继续或退出

### 3.2 工具系统

| 工具 | 参数 | 功能 | 风险等级 |
|------|------|------|---------|
| `read_file` | `path: str` | 读取文件内容（UTF-8） | 低 |
| `write_file` | `path: str, content: str` | 写入文件（覆盖） | 中 |
| `shell` | `cmd: str` | 执行 Shell 命令 | 动态评分 |
| `search` | `pattern: str, path: str` | 在项目中搜索代码（grep/glob） | 低 |

**约束**：
- 所有文件操作限定在 `workspace` 目录内
- Shell 命令默认超时 30 秒
- 工具执行结果统一封装为 `ToolResult(success, exit_code, stdout, stderr, error)`

### 3.3 治理护栏（重点维度）

四层防护：

| 层 | 名称 | 机制 | 触发条件 |
|----|------|------|---------|
| 1 | 模式匹配 + 风险评分 | 正则匹配危险命令模式 → 判定风险等级 | 每次 Shell / Write 工具调用 |
| 2 | 致命拦截 | 致命操作直接拒绝，不给审批机会 | `RiskLevel.FATAL` |
| 3 | HITL 审批 | 中/高风险操作暂停等待用户输入 y/N | `RiskLevel.MEDIUM` / `HIGH` |
| 4 | 范围围栏 | 禁止访问 workspace 外的路径和敏感目录 | 每次文件/Shell 操作 |

**风险等级**：

| 等级 | 说明 | 处置 |
|------|------|------|
| LOW | 安全操作（读文件、搜索） | 直接放行 |
| MEDIUM | 需注意（pip install、chmod） | HITL 审批 |
| HIGH | 高风险（git push --force、curl | sh） | HITL 审批 |
| FATAL | 不可接受（rm -rf /、DROP TABLE、覆写磁盘） | 直接拒绝 |

**HITL 状态机**：`IDLE → WAITING → (APPROVED / REJECTED / TIMEOUT) → IDLE`

### 3.4 反馈闭环

四个反馈信号，均为确定性解析器：

| 信号 | 解析器 | 输入 | 输出 |
|------|--------|------|------|
| 命令退出码 | 直接读取 | `ToolResult.exit_code` | 0=成功, 非0=失败 |
| 测试结果 | `TestParser` | stdout 文本 | `{passed, failed, errors}` |
| Lint 问题 | `LintParser` | stdout 文本（ruff/flake8 格式） | `[{file, line, message}]` |
| 类型错误 | `TypeCheckParser` | stdout 文本（mypy 格式） | `[{file, line, message}]` |

解析后的结构化反馈被格式化为文本，**回灌**到下一轮 LLM 调用的上下文中，驱动自我修正。

### 3.5 记忆系统

| 功能 | 存储位置 | 读写方式 |
|------|---------|---------|
| 项目约定（规则） | `.agent/rules.yaml` | 启动时读取，注入系统提示；CLI 可添加 |
| 历史决策日志 | `.agent/decisions.jsonl` | 每轮追加；最近 10 条注入上下文 |

### 3.6 配置系统

- **配置文件**：`.agent.yaml`（项目根目录），YAML 格式
- **CLI 参数**：`--max-rounds`、`--model`、`--no-guardrails`、`--workspace`
- **优先级**：CLI 参数 > 配置文件 > 默认值

---

## 4. 非功能性需求

### 4.1 性能

- Agent 单轮响应时间主要取决于 LLM API 延迟（不可控），Harness 自身处理时间 < 100ms
- Shell 工具默认超时 30s，可配置

### 4.2 安全

#### 凭据威胁模型

| 威胁 | 对策 |
|------|------|
| API Key 硬编码在源码中 | 绝不在代码中写 key；通过安全存储读取 |
| API Key 被提交到 Git | `.gitignore` 排除 `.env`、`credentials.*`、`.agent/secrets.*`；pre-commit hook 扫描 |
| API Key 在 shell history 中泄露 | 不通过环境变量命令行传入；使用隐藏输入 + 加密文件存储 |
| API Key 在日志/终端输出中泄露 | 输出中屏蔽 key（显示为 `****`） |
| 进程环境变量暴露 key | 不从环境变量读取；从加密文件按需加载到内存 |

#### 凭据存储方案

- **存储**：key 以 AES-256 加密存储在 `.agent/secrets.enc`（用户设置主密码）或系统钥匙串
- **录入**：首次运行 `python -m agent setup`，隐藏输入 key
- **查看**：`python -m agent status` 显示"已配置"或"未配置"，不回显明文
- **更新**：`python -m agent setup --force`
- **清除**：`python -m agent setup --clear`

### 4.3 可观测性

- 每轮执行打印：轮次、LLM 响应摘要、执行的动作、反馈摘要
- 护栏拦截打印：风险等级、原因、用户决策
- 错误打印：完整 traceback（key 除外）

### 4.4 可用性

- `docker build -t coding-agent . && docker run -it coding-agent "任务描述"` 一键启动
- README 包含完整引导流程

---

## 5. 系统架构

### 5.1 组件图

```
CLI (main.py)
    │
    ▼
ConfigLoader ──→ AgentLoop ──→ AgentResult
                    │
        ┌───────────┼──────────────┐
        ▼           ▼              ▼
  ContextBuilder  LLMAdapter   StopChecker
        │        (DeepSeek|Mock)
        ▼
    MemoryStore
        │
        ▼
    ActionParser
        │
        ▼
GuardrailCoordinator ← 重点维度
   │         │         │
   ▼         ▼         ▼
RiskScorer  HITLGate  ScopeFence
   │
   ▼
ToolExecutor
   │    │    │
   ▼    ▼    ▼
 File Shell Search
   │
   ▼
FeedbackCollector
   │    │    │    │
   ▼    ▼    ▼    ▼
ExitCode Test Lint Type
 Parser Parser Parser Parser
```

### 5.2 数据流

```
用户任务 → 上下文组装 → [LLM] → 动作解析 → [护栏] → [工具执行] → [反馈收集] → 停机判断
              ↑                                          │               │
              │              记忆写入 ←─────────────────┘               │
              │                                                          │
              └────────── 反馈回灌（未完成时）←───────────────────────────┘
```

### 5.3 外部依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| `openai` Python SDK | 调用 DeepSeek API（兼容 OpenAI 接口） | ≥1.0 |
| `pyyaml` | 配置文件解析 | ≥6.0 |
| `pytest` | 测试框架 | ≥8.0 |
| `cryptography` | 凭据加密 | ≥41.0 |

---

## 6. 数据模型

### 6.1 核心实体

```
Message:
    role: "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None

LLMResponse:
    content: str
    tool_calls: list[ToolCall] | None
    finish_reason: "stop" | "tool_calls" | "error"

ToolCall:
    tool_name: str
    args: dict[str, Any]

ToolResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    error: str | None
    tool_name: str

RiskResult:
    level: "LOW" | "MEDIUM" | "HIGH" | "FATAL"
    reason: str

GuardResult:
    blocked: bool
    reason: str

Feedback:
    exit_code: int
    success: bool
    test_result: TestResult | None
    lint_issues: list[LintIssue]
    type_errors: list[TypeError]

AgentResult:
    success: bool
    summary: str
    rounds: int
    error: str | None

Decision:
    timestamp: str
    action: ToolCall
    result_summary: str
    user_approval: bool | None
```

### 6.2 存储

| 实体 | 存储格式 | 位置 |
|------|---------|------|
| 项目规则 | YAML | `.agent/rules.yaml` |
| 决策日志 | JSONL | `.agent/decisions.jsonl` |
| 凭据 | AES-256 加密 | `.agent/secrets.enc` |
| 配置 | YAML | `.agent.yaml` |

---

## 7. 凭据与分发设计

### 7.1 凭据安全

- **存储**：DeepSeek API Key 使用 AES-256-GCM 加密存储，密钥由用户设置的主密码派生（PBKDF2）
- **录入流程**：`python -m agent setup` → 隐藏输入 API Key → 设置主密码 → 加密存储
- **运行时加载**：启动时输入主密码 → 解密 key → 仅存内存
- **绝不**：硬编码、环境变量明文、Git 提交、日志输出

### 7.2 分发

- **形态**：Docker 容器
- **获取**：`git clone <repo> && cd coding-agent-harness && docker build -t coding-agent .`
- **运行**：`docker run -it -v $(pwd):/workspace coding-agent "你的任务"`
- **Key 配置**：首次运行自动进入 setup 引导；或 `docker run -it coding-agent setup`
- **已知限制**：仅支持 Linux/x86_64 容器；需要互联网连接调用 DeepSeek API

---

## 8. 技术选型与理由

| 选项 | 选择 | 理由 |
|------|------|------|
| **语言** | Python 3.11+ | LLM SDK 生态最成熟；快速原型；pytest 测试框架丰富 |
| **LLM 供应商** | DeepSeek | 国产、性价比高、代码能力强、API 兼容 OpenAI SDK |
| **LLM SDK** | `openai` Python SDK | DeepSeek 兼容 OpenAI 接口，无需额外 SDK |
| **测试** | pytest | Python 生态标准、mock 注入方便 |
| **配置** | YAML | 人类可读写、Python 生态成熟（PyYAML） |
| **凭据加密** | cryptography 库 | AES-256-GCM + PBKDF2，工业标准 |
| **分发** | Docker | 一键运行、无 Python 环境依赖、CI 天然衔接 |
| **CLI 框架** | argparse | Python 标准库、零依赖 |
| **前端** | 无（纯 CLI） | 豁免 Open Design 要求 |

---

## 9. 验收标准

| 功能 | 验收方式 |
|------|---------|
| Agent 主循环 | `pytest tests/test_loop.py` 全部通过（Mock LLM） |
| 工具分发 | `pytest tests/test_tools.py` 覆盖 4 个工具的注册与执行 |
| 护栏拦截（重点） | `pytest tests/guardrails/` 覆盖：模式匹配、风险评分、致命拦截、HITL 审批、范围围栏 |
| 反馈闭环 | `pytest tests/feedback/` 覆盖：退出码解析、测试结果解析、lint 解析、类型检查解析 |
| 机制演示① | Mock LLM 下，危险动作被护栏拦截并报告 |
| 机制演示② | Mock LLM 下，注入测试失败 → Agent 收到反馈 → 下一轮动作改变 |
| 机制演示③ | Mock LLM 下，自定义护栏规则生效 |
| 真实 LLM 集成 | `python -m agent run "写一个 hello world 函数"` → 生成代码并运行测试通过 |
| 凭据安全 | `grep -r "sk-" src/` 无结果；`.gitignore` 排除敏感文件 |
| 分发 | `docker build -t coding-agent .` 成功；`docker run coding-agent --help` 输出帮助信息 |

---

## 10. 风险与未决问题

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| DeepSeek API 不稳定 | LLM 调用失败 | 最多 3 次重试 + 指数退避 |
| LLM 输出格式不一致 | 动作解析失败 | 解析器做容错处理 + 错误回灌让 LLM 重试 |
| Shell 工具执行恶意命令 | 主机安全风险 | 护栏拦截 + Docker 容器隔离；生产环境建议 Docker-in-Docker |
| Mock LLM 过于简单 | 遗漏真实 LLM 的边界行为 | 覆盖正常路径 + 错误路径 + 空响应 + 异常格式 |
| 凭据加密主密码遗忘 | 需要重新设置 key | `--force` 覆盖并提供说明 |
| Docker 镜像体积过大 | 分发不便 | 多阶段构建 + `python:3.11-slim` 基础镜像 |

---

## 11. 领域与机制设计（Coding Agent Harness 专属）

### 11.1 领域分析

**Coding Agent 的工作域**：
- 接收开发任务（修 bug、加功能、重构）
- 读写源代码文件
- 执行构建、测试、lint 命令
- 根据命令执行结果调整策略

### 11.2 机制设计

#### 动作/工具
Coding Agent 需要 4 个核心工具：`read_file`、`write_file`、`shell`、`search`。通过 `ToolRegistry` 注册，`ToolExecutor` 分发。每个工具有明确的参数 schema、风险等级、超时设置。

#### 客观反馈信号
四类确定性反馈：命令退出码（0/非0）、测试结果（pytest 输出解析）、Lint 问题（ruff/flake8 输出解析）、类型检查错误（mypy 输出解析）。每个都是纯函数解析器——输入字符串，输出结构化数据。**不是"让 LLM 检查"的提示词。**

#### 危险动作
Shell 命令的风险最高。危险动作通过正则模式库识别（`rm -rf /`、`DROP TABLE`、`curl | sh` 等），分四级（低/中/高/致命）。致命直接拒绝，中/高请求人工审批（HITL），低风险自动放行。文件写操作通过范围围栏限制在 workspace 内。

#### 记忆
最低实现：项目约定存 `.agent/rules.yaml`，历史决策存 `.agent/decisions.jsonl`。启动时注入系统提示，每轮追加新决策。信息按需提供给 LLM（最近 N 条），不全文载入。

### 11.3 重点维度：治理护栏

选择治理护栏作为主要贡献，理由：
1. 核心逻辑完全确定性——模式匹配 + 风险评分 + 状态机——与 mock 单测天然契合
2. 深入路径自然：四层防护 → 可配置规则 → HITL 状态机 → 范围围栏 → 审计日志
3. 与机制演示完美对齐：演示①护栏拦截、演示③扩展护栏
4. 课程核心关切：Agent 安全不能依赖 LLM 的"自律"，必须用代码落实

### 11.4 机制编码实现方式

所有机制满足 §A.4(C) 的判定标准——移除真实 LLM 后，每个机制都能用确定性单测验证：

| 机制 | 单测方式 |
|------|---------|
| 工具分发 | `ToolExecutor.execute(mock_action)` → 断言返回正确的 ToolResult |
| 治理拦截 | `GuardrailCoordinator.check(mock_action)` → 断言 blocked=True，替换 action 参数验证不同风险等级 |
| 反馈回灌 | `FeedbackCollector.collect(mock_result)` → 断言解析出正确的 TestResult / LintIssue / TypeError |
| 记忆读写 | `MemoryStore.record()` → `MemoryStore.get_recent_decisions()` → 断言一致 |
| 停机判断 | `StopChecker.should_stop(mock_feedback, round=N)` → 断言退出/继续 |

**不满足标准的"伪机制"（我们不会这样做）**：
- ❌ 在系统提示中写"请自行检查代码是否正确"
- ❌ 在提示中写"不要执行危险命令"
- ❌ 依赖 LLM 判断何时停止

---

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-08-10 | 初始版本，brainstorming 产出 |
