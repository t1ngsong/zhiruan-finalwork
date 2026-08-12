# SPEC_PROCESS.md — 过程文档

> Coding Agent Harness · AI4SE 期末项目 · A 方向

---

## 1. Brainstorming 关键节点

### 1.1 初始方向选择（2026-08-10）

在阅读课程要求后，面临两个方向的选择：

- **A 方向**：Coding Agent Harness（构建 Agent 的基础设施）
- **B 方向**：非 harness 应用类项目

选择 A 方向，理由：
1. 课程核心命题是"Agent = LLM + Harness"，A 方向直接回应这个命题
2. Harness 要求自己编码主循环、工具分发、护栏、反馈闭环——有明确的工程深度
3. Mock LLM 确定性测试是独特的挑战
4. 更贴近课程"理解 AI 系统本质"的教学目标

### 1.2 技术选型决策链

| 决策点 | 选项 | 选择 | 理由 |
|--------|------|------|------|
| 编程语言 | Python / TypeScript / Go | **Python 3.11+** | LLM SDK 生态最成熟，pytest 测试框架丰富 |
| LLM 供应商 | DeepSeek / 通义千问 / 智谱 | **DeepSeek** | 国产、性价比高、代码能力强、兼容 OpenAI SDK |
| 重点维度 | 治理护栏 / 反馈闭环 / 扩展 | **治理护栏** | 核心逻辑完全确定性（正则匹配+风险评分+状态机），与 mock 单测天然契合 |
| 配置格式 | YAML / TOML / JSON | **YAML** | 人类可读写，Python 生态成熟 |
| 凭据加密 | AES-256-GCM + PBKDF2 | **cryptography** | 工业标准 |
| 分发方式 | Docker / pip / 二进制 | **Docker** | 一键运行、无 Python 环境依赖 |
| CLI 框架 | argparse / click / typer | **argparse** | Python 标准库、零依赖 |
| 前端 | 无（纯 CLI） | **豁免** | 参照 Open Design 要求豁免 |

### 1.3 工具系统设计决策

课程要求"至少 3 个工具"，讨论后确定 4 个：

| 工具 | 风险 | 理由 |
|------|------|------|
| `read_file` | LOW | 只读操作，workspace 内安全 |
| `write_file` | MEDIUM | 修改文件，需范围围栏 |
| `shell` | 动态评分 | 风险最高，需模式匹配+审批 |
| `search` | LOW | 只读操作，grep 语义安全 |

反馈信号选择全部 4 种：退出码、测试结果、lint 问题、类型错误。

记忆系统选择最低实现：项目约定（`.agent/rules.yaml`）+ 历史决策（`.agent/decisions.jsonl`）。

## 2. 三轮关键迭代

### 第一轮：架构设计迭代（2026-08-10）

**初始方案**：简单的 "LLM → 工具 → 反馈" 循环，所有组件耦合在一起。

**发现的问题**：通过自检发现架构不够清晰，组件间耦合度高，mock 测试困难。

**修正**：
- 引入顺序管道架构：CLI → 配置 → 上下文 → LLM → 解析 → 护栏 → 工具 → 反馈 → 停机
- 每层独立，可独立单测
- LLM 抽象层使用 ABC + MockAdapter + DeepSeekAdapter 三实现
- 护栏采用四层防护：模式匹配 → 风险评分 → HITL 审批 → 范围围栏

### 第二轮：护栏深度设计迭代（2026-08-10）

**初始方案**：简单的正则匹配 + 黑白名单。

**发现的问题**：通过头脑风暴发现护栏应该有层次——不是所有"危险"都应该直接拒绝，也不是所有"安全"都应该放行。

**修正**：
- 引入四级风险等级：LOW / MEDIUM / HIGH / FATAL
- FATAL 直接拒绝（`rm -rf /`、`DROP TABLE`）
- MEDIUM/HIGH 触发 HITL 审批（60 秒超时）
- LOW 自动放行
- 增加范围围栏防止工作区外的路径访问
- HITL 状态机：IDLE → WAITING → (APPROVED / REJECTED / TIMEOUT) → IDLE

### 第三轮：SPEC 自检与修正（2026-08-10）

**发现的问题**：
1. SPEC 中工具数量不一致（§3.2 写 4 个，§9 和 §11.2 写"3个"）
2. 文件操作路径穿越防护设计不足
3. 凭据管理缺少"清除"功能
4. 配置优先级未明确

**修正**：
1. 统一工具数量为"4个"
2. 增加路径穿越防护设计（`is_relative_to`）
3. 增加 `setup --clear` 命令
4. 明确 CLI 参数 > 配置文件 > 默认值 的优先级链

## 3. 冷启动验证记录

### 验证方法

按照课程要求，用不同的 Agent（Codex CLI，与主开发用的 Claude Code 不同）仅凭 SPEC + PLAN 试实现 1-2 个 task。

### 试实现 Task：Action Parser（动作解析器）

**输入**：仅提供 SPEC.md 和 PLAN.md，不提供任何其他上下文。

**结果**：
- ✅ 成功创建 `src/agent/parser.py` 和 `tests/test_parser.py`
- ✅ 实现了 TEXT / TOOL_CALL / FINISH 三种类型的解析
- ✅ 测试覆盖正常路径和 JSON 解析失败边界
- ⚠️ FINISH 检测使用了更宽泛的关键词匹配（"DONE"、"完成"、"COMPLETE"），与 SPEC 中的严格 `response.content.strip().upper().startswith("FINISH")` 有差异

**发现**：
1. SPEC 中对 FINISH 检测的描述不够精确——"FINISH" 关键词检测应该是开头精确匹配还是包含匹配需要明确
2. PLAN 中任务 3 的依赖描述正确（依赖 Task 2 的 LLMResponse）

**SPEC 修正**：在 SPEC 中补充了 FINISH 检测的精确语义。

## 4. SPEC 最终结构

SPEC.md 共 11 个章节：

| 章节 | 内容 | 页数估算 |
|------|------|---------|
| §1 | 问题陈述 | 目标用户、为什么值得做 |
| §2 | 用户故事 | 7 个 INVEST 用户故事 |
| §3 | 功能规约 | 主循环、工具系统、护栏（重点）、反馈、记忆、配置 |
| §4 | 非功能性需求 | 性能、安全、可观测性、可用性 |
| §5 | 系统架构 | 组件图、数据流图、外部依赖 |
| §6 | 数据模型 | 12 个核心实体 |
| §7 | 凭据与分发设计 | 威胁模型、存储方案、分发形态 |
| §8 | 技术选型与理由 | 9 项技术决策 |
| §9 | 验收标准 | 12 条验收条件 |
| §10 | 风险与未决问题 | 6 个风险及缓解措施 |
| §11 | 领域与机制设计 | 专属机制分析、重点维度说明 |

## 5. 变更记录

| 日期 | 变更 |
|------|------|
| 2026-08-10 | 初始 brainstorming，产出 SPEC v1 |
| 2026-08-10 | 自检修正：工具数量、路径穿越、凭据清理、配置优先级 |
| 2026-08-10 | 冷启动验证：Action Parser 试实现，FINISH 语义澄清 |
| 2026-08-10 | 最终 SPEC 定稿，转入 writing-plans |
