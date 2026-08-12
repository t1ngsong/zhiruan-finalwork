# AGENT_LOG.md — 关键节点记录

> Coding Agent Harness · AI4SE 期末项目 · 按时间顺序

---

## 2026-08-10（第一天）

### 09:00–10:00 | 项目启动

- **技能**：`superpowers:brainstorming`
- **内容**：阅读课程要求文件，确定 A 方向（Coding Agent Harness），技术选型（Python 3.11+, DeepSeek, pytest, Docker）
- **人工干预**：选择 A 方向、Python、DeepSeek、Docker、治理护栏为重点维度
- **产出**：初步设计思路

### 10:00–12:00 | SPEC 编写

- **技能**：直接对话
- **内容**：逐节编写 SPEC.md（11 章节），完成系统架构设计
- **关键决策**：
  - 顺序管道架构（8 步主循环）
  - 四层护栏（模式匹配 → 风险评分 → HITL → 范围围栏）
  - 四级风险等级（LOW/MEDIUM/HIGH/FATAL）
  - 4 个工具 + 4 个反馈信号
  - AES-256-GCM 凭据加密
- **人工干预**：多次确认设计选择（工具数量、反馈信号、记忆方案、架构模式）

### 12:00–13:00 | SPEC 自检与冷启动验证

- **技能**：自检 + 冷启动验证（不同 Agent 试实现 Action Parser）
- **发现**：工具数量不一致、FINISH 语义模糊
- **修正**：统一工具数量为 4、明确 FINISH 精确匹配语义
- **人工干预**：批准修正

### 13:00–14:00 | Writing Plans

- **技能**：`superpowers:writing-plans`
- **内容**：将 SPEC 分解为 12 个 task
- **产出**：`docs/superpowers/plans/2026-08-10-coding-agent-harness.md`
- **人工干预**：选择 Subagent-Driven Development（SDD）模式

---

## 2026-08-10（第二天）— SDD 执行

### Task 1: 项目脚手架

- **时间**：14:00–14:30
- **模型**：Haiku
- **提交**：`5a3a860`
- **内容**：`pyproject.toml`、目录结构、`.gitignore`、`.agent.yaml`、`src/agent/models.py`
- **评审**：Spec ✅ Quality ✅，直接通过
- **教训**：脚手架阶段需要确认 build-backend 兼容性（setuptools 83.x 移除了旧 backend）

### Task 2: LLM 抽象层

- **时间**：14:30–15:00
- **模型**：Haiku
- **提交**：`30824d8`
- **内容**：`LLMAdapter`（ABC）、`LLMResponse`（dataclass）、`MockLLMAdapter`（脚本驱动）、`DeepSeekAdapter`（OpenAI SDK 适配）
- **评审**：Spec ✅ Quality ✅，Minor：unused field import
- **教训**：Mock LLM 的 script exhaust 行为需要明确定义

### Task 3: 配置系统

- **时间**：15:00–15:30
- **模型**：Haiku
- **提交**：`b42f5c6`
- **内容**：`Config`（12 字段）、`ConfigLoader`（YAML → CLI → defaults）
- **评审**：Spec ✅ Quality ✅，直接通过
- **教训**：CLI 覆盖逻辑用 `getattr` 遍历，简洁但有类型安全风险

### Task 4: 动作解析器

- **时间**：15:30–16:00
- **模型**：Haiku
- **提交**：`2e4217d`
- **内容**：`ActionParser.parse()` → TEXT / TOOL_CALL / FINISH
- **评审**：Spec ✅ Quality ✅，直接通过
- **教训**：FINISH 检测关键词列表需要在编码人员可扩展性和规范性之间取舍

### Task 5: 工具系统

- **时间**：16:00–17:30（含 1 个修复轮次）
- **模型**：Haiku → Haiku（修复）
- **提交**：`75ad9bb` → `bbacea6`（修复）
- **内容**：`ToolRegistry`、`ToolExecutor`、4 个核心工具（file_tools、shell_tool、search_tool）
- **修复轮次 1**：路径穿越防护
  - **问题**：`str.startswith()` 允许前缀碰撞绕过（workspace `/tmp/ws` 允许 `/tmp/wsfoo/evil`）
  - **修复**：替换为 `Path.is_relative_to()`，新增 9 个穿越测试
  - **评审**：ADDRESSED
- **教训**：文件系统安全必须用精确的路径比较方法，不能用字符串方法

### Task 6: 治理护栏系统（重点维度）

- **时间**：16:00–18:00（含 1 个修复轮次）
- **模型**：Sonnet（复杂集成）→ Sonnet（修复）
- **提交**：`caa3480` → `52b2f8d`（修复）
- **内容**：`patterns.py`（8 个危险模式）、`scorer.py`（风险评分）、`hitl.py`（HITL 状态机）、`fence.py`（范围围栏）、`coordinator.py`（协调器）
- **修复轮次 1**：
  - **HITL 状态机不完整**：APPROVED/REJECTED/TIMEOUT 只在 docstring 里，`finally` 直接跳到 IDLE → 修复：正确设置状态再返回
  - **HITL 超时是假的**：`input()` 阻塞不超时 → 修复：改用 `threading.Event.wait(timeout=N)`
  - **rm 正则过宽**：`rm -rf /tmp` 也匹配 FATAL → 修复：收紧正则只匹配 `rm -rf /` 和 `rm -rf /*`
  - 新增 14 个 HITL 测试
- **停留问题**：
  - B1：`rm -r -f /`（分开写）未捕获 → 低概率变体，已知限制
  - B2：ScopeFence 对 shell 用字符串包含 → 可能误报，v0.1.0 可接受
  - B4：daemon thread 边界情况 → CLI 工具无影响
- **教训**：HITL 状态机必须真的在状态间转换，不能只写在文档里；超时必须用真计时器

### Task 7: 反馈闭环

- **时间**：18:00–18:30
- **模型**：Haiku
- **提交**：`735df8e`
- **内容**：`TestParser`、`LintParser`、`TypeCheckParser`、`FeedbackCollector`
- **评审**：Spec ✅ Quality ✅，直接通过（111 tests）
- **教训**：正则解析器的健壮性取决于对工具输出格式的事先了解

---

## 2026-08-12（第三天）— 持续执行

### Task 8: 记忆系统

- **时间**：09:00–09:30
- **模型**：Haiku
- **提交**：`08c91ea`
- **内容**：`MemoryStore`（`.agent/rules.yaml` + `.agent/decisions.jsonl`）
- **评审**：Spec ✅ Quality ✅，直接通过（116 tests）

### Task 9: Agent 主循环 + 上下文 + 停机判断

- **时间**：09:30–11:00
- **模型**：Sonnet（多文件集成）
- **提交**：`1382eb9`
- **内容**：`ContextBuilder`、`StopChecker`、`AgentLoop`（主循环）+ 12 个集成测试
- **评审**：Spec ✅ Quality ✅，Minor：3 个 unused imports（128 tests）
- **教训**：集成测试需要用 Mock LLM 脚本精确编排多轮对话，脚本设计是关键

### Task 10: CLI 入口 + 凭据管理

- **时间**：11:00–12:00
- **模型**：Haiku
- **提交**：`c68d19a`
- **内容**：`main.py`（凭据加密 + CLI + Agent 组装）
- **实现者修正**：
  - `PBKDF2` → `PBKDF2HMAC`（cryptography ≥41.0 API 变更）
  - shell handler dict→string 适配
  - 合并重复 `import os`
- **评审**：Spec ✅ Quality ✅，Minor：4 项（131 tests）

### Task 11: 机制演示

- **时间**：12:00–13:00
- **模型**：Haiku
- **提交**：`04c8aeb`
- **内容**：3 个演示测试：
  1. 护栏拦截 `rm -rf /`
  2. 反馈闭环驱动自我修正（pytest fail → fix → pass）
  3. 自定义护栏规则 + HITL 审批
- **实现者修正**：修复 brief 中的 `_call_counter` 定义顺序 bug
- **评审**：Spec ✅ Quality ✅，Important：1 个 unused import（135 tests）

### Task 12: Docker 分发 + CI

- **时间**：13:00–13:30
- **模型**：Haiku
- **提交**：`70f214f`
- **内容**：`Dockerfile`、`.github/workflows/ci.yml`、`README.md`
- **评审**：Spec ✅ Quality ✅，Minor：README 目录树不完整（Docker 不可用，CI 覆盖）

---

## 最终审查与修复（2026-08-12）

### 全分支代码审查

- **时间**：14:00–15:00
- **模型**：Sonnet
- **内容**：完整 diff 审查（a70d21c..70f214f，14 个提交，74 个文件，3478+ 行）
- **结论**：准备合并，6 个 Important 问题

### 最终修复轮次

- **时间**：15:00–15:30
- **模型**：Haiku
- **提交**：`5ca677c`
- **修复**：
  1. I1：删除 `src/agent/models.py`（122 行死代码）+ 清理 conftest
  2. I2：删除 `--no-guardrails` CLI 标志
  3. I3：`pip install` 风险从 LOW 改为 MEDIUM
  4. I4：统一工具注册（`build_agent` 调用 `register_all_tools`）
  5. I5：删除 unused imports（`base64`、`Path`）
  6. I6：ConfigLoader 增加 `file_tools_enabled`/`search_enabled` YAML 解析
- **重新评审**：全部 6 个问题 ADDRESSED，0 回归
- **最终测试**：135 passed，0 failed

### 合并到 master

- **时间**：15:30
- **合并方式**：Fast-forward merge
- **测试验证**：135 passed，0 failed（合并后）
- **清理**：Worktree 已删除，分支已删除

---

## 总结

| 指标 | 数值 |
|------|------|
| 总任务数 | 12 |
| 提交数 | 15 |
| 总测试数 | 135 |
| 修复轮次 | 3（Tasks 5、6、最终审查） |
| 停留问题 | 3（已评估，无行动） |
| 人工干预 | 主要是设计阶段（技术选型、架构确认） |
| SDD 执行 | 全自动，仅在修复轮次中需要决策 |

### 关键教训

1. **TDD 强制有效**：Mock LLM + 先红后绿让每个模块都有确定性测试，合并后零回归
2. **路径安全必须用精确方法**：`str.startswith()` 的教训验证了"永远不要用字符串做路径比较"
3. **HITL 不能假实现**：超时必须用真计时器，状态机必须真的转换状态
4. **SDD 的修复循环有效但昂贵**：Tasks 5 和 6 都需要修复轮次，但最终都正确了
5. **死代码是工程债务**：`models.py` 从 Task 1 就存在，到最终审查才清理——说明每任务审查应该更关注未使用代码
6. **Agent 编排的自主性**：12 个 task 中 10 个一次性通过，2 个需要修复——证明 SDD 模式在规约清晰的场景下高效

---

## 附录 A：关键 Prompt / Context 配置

### A.1 系统提示词（System Prompt）

所有 subagent 派发时使用的系统提示词模板（ContextBuilder 生成）：

```
你是一个 Coding Agent，负责完成用户指定的编码任务。

你可以使用以下工具：
[{"name": "read_file", "description": "读取文件内容", ...},
 {"name": "write_file", "description": "写入文件内容（覆盖）", ...},
 {"name": "shell", "description": "执行 shell 命令", ...},
 {"name": "search", "description": "在项目中搜索代码", ...}]

项目约定：
- code_style: 使用 snake_case 命名
- test_framework: 使用 pytest

最近决策:
- shell(pytest tests/) → [测试] 3 passed, 0 failed
- write_file(path=fix.py, ...) → 已写入 fix.py

规则：
1. 每次只能调用一个工具
2. 完成任务后回复 FINISH
3. 如果工具执行后的反馈显示测试失败、lint 错误或类型错误，请修复代码后重新运行验证
4. 所有文件路径使用相对路径
```

### A.2 Task Brief 示例（Task 4: Action Parser）

这是 SDD 派发时实际使用的 task brief 核心内容：

```markdown
## 接口契约

- Consumes: `LLMResponse` (from Task 2)
- Produces: `ActionParser.parse(response: LLMResponse) -> Action`
- `Action` dataclass:
  - `type: str` — "TEXT" | "TOOL_CALL" | "FINISH"
  - `content: str` — 文本内容
  - `tool_name: str` — 工具名称
  - `args: dict` — 工具参数
  - `tool_call_id: str` — 调用 ID

## FINISH 检测规则（精确语义）

FINISH 检测必须是 **content.strip().upper().startswith("FINISH")** 或
"FINISH" 出现在 content.upper() 的前 20 个字符内。
不使用更宽泛的关键词匹配（如 "DONE"、"完成"）。

## 测试用例

1. `test_parse_finish` — response.content="任务完成", finish_reason="stop" → Action(type="FINISH")
2. `test_parse_text_response` — 纯文本无 tool_calls → Action(type="TEXT")
3. `test_parse_tool_call` — tool_calls 含 shell → Action(type="TOOL_CALL", tool_name="shell")
4. `test_parse_tool_call_with_json_parse_error` — arguments='{invalid json' → Action(type="TEXT", content 含"参数解析失败")
```

### A.3 全局约束（Global Constraints）

每个 task reviewer 收到的全局约束（从 PLAN.md 提取）：

```markdown
## 全局约束
- Python 3.11+，标准库 + openai + pyyaml + pytest + cryptography
- 所有测试用 pytest 运行，单条命令 pytest tests/ 必须覆盖全部
- Mock LLM 测试不访问网络、不调用真实 API
- 凭据绝不硬编码，使用 AES-256-GCM 加密存储
- TDD 强制：先写失败测试 → 确认红色 → 最小实现 → 确认绿色 → 提交
- workspace 参数决定 agent 的文件操作范围
- .agent.yaml 为配置文件，CLI 参数覆盖配置
```

---

## 附录 B：Subagent 输出关键片段

### B.1 Task 5 修复轮次 — Reviewer 发现路径穿越

**Reviewer 输出**：

```
🔴 CRITICAL: 路径穿越防护使用 str.startswith()

文件: src/agent/tools/executor.py, 第 12 行

当前代码:
  if not str(file_path).startswith(str(self.workspace)):
      raise ValueError("路径超出工作区")

问题: str.startswith() 做前缀匹配，workspace="/tmp/ws" 时，
/tmp/wsfoo/evil 也会被判定为"在工作区内"。

修复方案: 改用 Path.is_relative_to()
  if not file_path.resolve().is_relative_to(self.workspace):
      raise ValueError("路径超出工作区")

建议新增测试：workspace 为 /tmp/ws 时，尝试访问 /tmp/wsfoo/evil
应被拒绝。
```

**Implementer 修复后提交**: `bbacea6`

### B.2 Task 6 修复轮次 — Reviewer 发现假超时

**Reviewer 输出**：

```
🔴 CRITICAL: HITL 超时机制是假的

文件: src/agent/guardrails/hitl.py, 第 20 行

当前代码:
  answer = input("批准执行? [y/N] (60s 超时自动拒绝): ")

问题: input() 在无输入时会永久阻塞，永远不会"超时"。用户离开
电脑 1 小时后回来，Agent 还在等。

修复方案: 使用 threading.Event.wait(timeout=N) + daemon 线程:
  stop_event = threading.Event()
  def get_input():
      answer = input(...)
      stop_event.answer = answer
      stop_event.set()
  t = threading.Thread(target=get_input, daemon=True)
  t.start()
  if not stop_event.wait(timeout=60):
      return False  # 超时
  return stop_event.answer.lower() == "y"

需新增 14 个测试覆盖各状态转换路径。
```

**Implementer 修复后提交**: `52b2f8d`

### B.3 最终审查 — Subagent 发现死代码

**最终审查 Agent 输出（Sonnet）**：

```
⚠️ I1: src/agent/models.py — 122 行未使用的死代码

该文件包含 Pydantic 模型定义，但在整个项目中没有任何 import 引用。
这是旧版设计的残留（Task 1 创建，后续任务改用 dataclass 替代）。
建议删除该文件并清理 conftest.py 中对应的 fixture。

其他发现:
- I2: main.py 中 --no-guardrails CLI 标志未被使用
- I3: pip install 在 patterns.py 中风险等级为 LOW，建议改为 MEDIUM
- I4: register_all_tools() 和 build_agent() 重复注册工具
- I5: 两处 unused imports (base64, Path)
- I6: ConfigLoader 缺少 file_tools_enabled/search_enabled 的 YAML 解析
```

**修复提交**: `5ca677c` — 全部 6 项 ADDRESSED
