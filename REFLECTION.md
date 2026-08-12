# REFLECTION.md — 反思报告

> Coding Agent Harness · AI4SE 期末项目 · A 方向
>
> *本文由学生撰写，AI 辅助润色（见文末标注）*

---

## 一、从"使用 Agent"到"构建 Agent"

在这个项目之前，我使用过 Claude Code、Cursor 等 Coding Agent 完成编码任务。它们像黑盒——我输入任务，它们输出代码，中间发生了什么我不清楚。Agent 执行了危险操作我只能事后补救，陷入循环我只能强制停止。

这个项目让我从 Agent 的**使用者**变成了 Agent 的**构建者**。我亲手实现了主循环的每一步：上下文组装 → 调用 LLM → 解析动作 → 护栏拦截 → 分发工具 → 收集反馈 → 写入记忆 → 判断停机。当 Mock LLM 脚本驱动的 Agent 在测试中自主完成"运行测试 → 发现失败 → 读取源码 → 修复代码 → 再次测试通过"这个闭环时，我第一次真正理解了课程的核心命题：**Agent = LLM + Harness**。

LLM 只是一个"下一步做什么"的决策器。它不知道什么是危险，不知道自己对错，不知道何时该停。所有这些都需要 Harness 这层工程机制来保障。这个认识不是读出来的，是写出来的——写 `GuardrailCoordinator`、写 `FeedbackCollector`、写 `StopChecker`。

---

## 二、Superpowers 技能：哪些真正有用，哪些流于形式？

### 真正发挥作用的技能

**Brainstorming** 是价值最大的技能。在我开始写代码之前，它逼着我对架构做了一系列决策：顺序管道 vs 事件驱动？四层 vs 两层护栏？YAML vs TOML？这些决策如果在编码阶段再做，每次改变的成本都远高于 brainstorming 阶段。它的追问模式——"你确定工具数量是 3 个而不是 4 个？"——迫使我面对自己想法中的模糊地带。

**SDD（Subagent-Driven Development）** 是效率最高的技能。12 个 task，每个派给一个新鲜 subagent，带着精确的 task brief 进入、交出 commit 离开。10 个 task 一次通过，2 个需要修复轮次——这个成功率在软件开发中相当高。关键因素是 task brief 的质量：每个 brief 都有精确的代码模板和测试用例，subagent 的任务是**转录和验证**，而非**从零设计**。

**TDD** 是质量保障的基石。135 个测试中每一个都使用 MockLLMAdapter，零网络调用，运行时间不到 2 秒。合并后零回归——这归功于 TDD 的"先红后绿"纪律。

### 流于形式的技能

**Finishing-a-development-branch** 在本项目中有点形式大于实质。它的"三选一菜单"（merge locally / create PR / keep as-is）是为团队协作设计的——PR review、CI 通过、合并审批——但我是一个人开发，最终就是 git checkout master && git merge --ff-only。真正有用的只有最后的清理步骤（worktree remove + prune），避免了残留 worktree 占着磁盘。技能本身没问题，只是它的使用场景和单人项目不匹配。

**Using-git-worktrees** 在我这个场景下也有点多余。我用的是 Claude Code 自带的 EnterWorktree 工具——它自己就会创建工作区、管理生命周期、会话结束时清理。再用 git-worktrees 技能去"检查是否已在 worktree 中"，等于平台做了一遍的事我又手动做一遍。如果用的是不支持原生 worktree 的工具，这个技能才有意义。

---

## 三、TDD 在 AI 协作下：阻碍还是放大器？

**是放大器，不是阻碍。**

Mock LLM 测试让这个判断变得清晰。传统的 TDD 瓶颈在于"写测试本身就花了大量时间"——但在这个项目中，subagent 同时生成实现和测试，测试的时间成本被 AI 分摊了。真正花时间的是**设计测试场景**：Agent 收到 `rm -rf /` 后护栏应该返回 FATAL？Agent 在第三轮调用后应该停机？这些场景设计需要人对 Harness 行为的理解，无法外包给 AI。

TDD 作为放大器的另一个证据在修复轮次中体现得最明显。Task 5（路径穿越）的修复新增了 9 个测试——先写测试、确认红色、再修复代码、确认绿色。如果反过来（先修代码再补测试），同样的路径穿越 bug 可能在另一个上下文下复现，因为没有测试把它"钉死"。

TDD 还解决了 AI 协作中一个隐蔽的问题：**过度自信**。Subagent 完成实现后声称"DONE"，如果没有测试的红色/绿色作为客观证据，你无法区分"DONE 代表真的完成了"还是"DONE 代表 subagent 以为完成了"。135 个绿色测试是 135 个客观证据——它们不依赖 subagent 的自我评价。

---

## 四、SDD 的自主性与 task 颗粒度

### 自主运行时间

在我的项目中，SDD 流程能让 subagent 自主运行约 15-30 分钟（一个 task 的完整周期）而不偏离主题。关键在于 task brief 的精确性：当 brief 包含了精确的函数签名、测试用例和预期行为时，subagent 偏离的概率很低。Task 4（Action Parser）的 brief 甚至包含了 FINISH 检测的精确正则——subagent 几乎没有自由发挥的空间。

反之，当 brief 留了"实现一个安全的护栏系统"这种开放式描述时（Task 6 的初版 brief），subagent 就会做出"input() = 超时"这种看似合理但实际错误的假设。Task 6 是唯一需要 Sonnet 模型 + 修复轮次的 task，这并非巧合。

### 最优 task 颗粒度

我的经验是：**一个 task = 一个模块 + 一个测试文件**。具体来说：
- 2-4 个源文件
- 1 个测试文件
- 5-20 个测试用例
- Subagent 可在 15-30 分钟内完成

超过这个范围（如 Task 6 跨越 5 个模块），subagent 的上下文开始碎片化，遗漏跨模块约束的概率上升。小于这个范围（如把"写一个 dataclass"单独作为 task），派发 subagent 的 overhead 超过了实际编码时间。

---

## 五、SPEC 质量如何影响实现质量

最典型的案例是 **SPEC 中工具数量的不一致**。

在 SPEC v1 中，§3.2 写了 4 个工具（read_file / write_file / shell / search），但 §9 验收标准和 §11.2 领域设计写的是"3 个工具"。这个不一致在冷启动验证中被发现：第二个 Agent 读完 SPEC 后询问"到底要实现 3 个还是 4 个工具？"——它停在了这个矛盾上，无法继续。

如果这个不一致没有被发现就进入 SDD 阶段，不同的 subagent 可能基于不同的数字来实现——Task 5（工具系统）实现 4 个工具，Task 12（机制演示）的测试用 3 个工具——合并时就会产生集成冲突。这验证了课程强调的"冷启动验证用不同 Agent"的价值：**共享的隐性上下文会让你严重高估 spec 的清晰度**。

另一个例子是 FINISH 检测的语义。SPEC 初版只说"检测 LLM 返回的 FINISH 关键词"，但没有说明是开头精确匹配还是包含匹配。冷启动验证的 Agent 使用了更宽泛的包含匹配（"DONE"、"完成"都算 FINISH），而主开发 Agent 的 SPEC 意图是 `response.content.strip().upper().startswith("FINISH")`。这个差异暴露后，SPEC 中补充了精确语义。

**教训**：SPEC 中每一个"看起来显然"的约定，在脱离对话上下文后都会变成歧义。数字、精确匹配 vs 包含匹配、字段类型——这些细节必须写进 SPEC，不能靠"开发者应该懂"来弥补。

---

## 六、最有效的 prompt / context 策略

### 1. Task brief 即合约

最有效的策略是把 task brief 写成一份**精确的合约**，而不是一段开放式的描述。好的 brief 包含：
- 精确的函数签名（含类型注解）
- 测试用例的输入和预期输出（用代码块给出）
- 禁止使用的模式（如"不得使用 str.startswith() 做路径比较"）

坏的 brief："实现一个工具系统，支持读写文件和执行命令"。好的 brief："实现 `ToolRegistry.register(name, handler)` 和 `ToolExecutor.execute(name, params)`，handler 签名见附录 A，测试用例见附录 B"。

Task 2-4、7-8、10-12 都使用这种"合约式 brief"，全部一次通过。Task 5 和 6 的 brief 相对开放，都进了修复轮次。

### 2. 模型分层使用

Haiku 用于机械性 task（1-5、7-8、10-12），Sonnet 用于需要跨文件判断的集成 task（6、9、最终审查）。这个策略在成本可控的前提下保证了质量——12 个 task 中只有 2 个用了 Sonnet，但它们恰好是复杂度最高的 task。

### 3. 修复轮次中保持 implementer

Rounds 1-3 使用同一个 implementer（通过 SendMessage 续接上下文），而不是每次都派新 agent。这是因为修复通常是小范围改动，原 implementer 对代码的上下文记忆比重新读 diff 更高效。

---

## 七、凭据与分发：逼你想清楚的事

凭据管理迫使我想清楚了**"key 在哪里、谁能读到、怎么转手"**这个链条上的每一个环节。

- **key 在哪里**：不在源码里（`.gitignore` 排除 `.env`）、不在 git 历史里（使用 `setup` 命令交互式录入而非文件编辑）、不在终端 history 里（隐藏输入 `getpass`）、不在日志里（日志输出自动脱敏）。
- **谁能读到**：主密码 + AES-256-GCM 加密存储，加密前通过 PBKDF2HMAC 600,000 次迭代派生密钥，即使 `.agent/credentials.enc` 文件泄露，没有主密码也无法解密。
- **怎么转手**：Docker 镜像分发给另一个用户时，那个人需要自己运行 `agent setup` 录入 DeepSeek API Key——key 不会被我打包进镜像。

这些如果不在项目要求中显式提出，我大概率会走捷径："用环境变量就行了"→ 然后不小心 `echo $API_KEY` 进终端历史 → 或者 commit 了 `.env` 文件 → 或者在 Docker 镜像里 bake 了明文 key。**安全不是"做了没有"，而是"在每个可能的泄露路径上都设了卡点没有"**。

分发（Docker）迫使我想清楚了**"别人怎么跑起来"**。`docker build && docker run` 看起来简单，但里面藏着很多细节：Python 版本（3.11-slim）、依赖安装（`pip install -e .`）、工作目录、卷挂载（`-v $(pwd):/workspace`）、key 从哪里来（`-e DEEPSEEK_API_KEY` 或容器内 `agent setup`）。README 里的"Quick Start"章节不是在写文档——是在验证分发方案是否真的可行。

---

## 八、如果重做，我会改变什么

### 1. 更早引入集成测试

Tasks 1-8 都是单元模块，各自功能正确。Task 9 把它们串起来时才发现接口摩擦：`execute_shell` 返回 dict 但 `ToolExecutor` 期望 string、`Config.workspace` 是 string 但 `ScopeFence` 期望 `Path`。如果 Task 2 完成后就有一个端到端骨架测试（用 Mock LLM 跑一轮完整循环），这些摩擦会更早暴露。

### 2. 从第一天就统一工具注册

`register_all_tools()` 和 `build_agent()` 各自注册工具，配置不同、参数不同——这个问题到最终审查才修复。正确的做法是让 `build_agent()` 从一开始就调用 `register_all_tools()`。SDD 的一个盲点是：**跨 task 的代码重复问题，没有一个 task brief 会覆盖到**。

### 3. 护栏规则可配置化

当前 8 个危险模式硬编码在 `patterns.py` 里。如果要添加新规则，需要改代码而非配置。虽然 Demo 3 测试了通过 `.agent.yaml` 的 `custom_patterns` 字段注入自定义规则，但内置的 8 个模式同样应该可配置。

### 4. 反馈信号更丰富

当前 4 个解析器（退出码 / 测试结果 / lint / 类型检查）覆盖了基本场景，但还可以加：diff 解析器（Agent 修改了哪些行、多少行）、覆盖率解析器（测试覆盖率升了还是降了）。多一个反馈信号，Agent 就多一个判断"我做对了吗"的依据。

---

## 九、对 Superpowers 方法论的批判

### Superpowers 的核心假设

1. **"规约足够清晰，subagent 就能正确执行"**。这个假设在 Task 1-4、7-8、10-12 中成立——这些 task 的规约可以精确到"函数签名 + 测试用例"级别。但在 Task 5（工具系统 + 安全）和 Task 6（护栏 + HITL 状态机）中不完全成立——安全的边界条件（"`str.startswith()` 在什么情况下被绕过"）很难在规约中穷举。

2. **"两阶段评审（spec compliance + code quality）能捕获所有重要问题"**。这个假设在大多数 task 中成立，但它有一个盲区：**跨 task 的代码质量问题**。Task 1 创建的 `models.py` 死代码（122 行）到 Task 12 还在代码库里，因为 task-scoped reviewer 只审当前 diff，不会检查"这个文件是否被使用"。全局死代码、重复注册、命名不一致——这些都是 task-scoped review 的系统性盲区。

3. **"修复循环（max 5 rounds）足以解决所有实现问题"**。Task 5 和 Task 6 都在 Round 1 修复成功，没有触发更高级的修复轮次（R4-5 换模型）。所以我无法验证"换更强大的模型能解决 implementer 被卡住的问题"这个假设——但理论上合理。

### 在我的项目中成立吗？

成立，但打了折扣。在我这个项目中，大部分 task 规约清晰、模块独立，Superpowers 跑得很顺。但有两个地方它明显吃力：

- **安全敏感代码**（护栏、路径穿越防护）。`str.startswith()` 会被前缀碰撞绕过——这个边界条件在写 SPEC 的时候我完全没想到。Reviewer 如果不带安全攻防的思维去读代码，只做"spec vs code"的机械对照，是发现不了这种问题的。Task 5 的修复恰恰是因为 reviewer 有安全背景，而不是因为 review 流程本身设计得好。
- **跨 task 的质量问题**。`models.py` 这个 122 行的死文件从 Task 1 残留到 Task 12，因为它不是任何一个 task reviewer 的"管辖范围"。最终审查（全分支 diff）发现了它，但此时它已经默默存在了 11 个 commit。这个锅不能全甩给 Superpowers——每个方法论都有盲区——但它确实说明 task-scoped review 需要搭配全局扫描才能完整。

### 课程核心命题的最终回答

这个项目让我对"工程师的价值在哪里"形成了三个层次的回答：

**第一层——判断"做什么"**：LLM 能写代码，但不知道这段代码是否应该存在。12 个 task brief 的精确性决定了 SDD 的成功率，而 brief 的精确性来源于人对需求的判断。

**第二层——判断"做对了吗"**：LLM 不知道自己的输出是否正确。工程师设计确定性验证机制——测试、护栏、反馈闭环——这些机制是代码，不是提示词。

**第三层——构建可信的系统**：单次 LLM 调用不可靠，但把 LLM 嵌入确定性工程框架后，系统整体可以可靠。这就是 Harness 的价值。这个洞察超越了 Coding Agent：**任何 AI 应用，如果要做到生产级可靠，都需要类似的工程化封装**。

---

*2026-08-12 · 南京大学 · AI4SE*

*标注：本文由学生撰写核心观点与全部具体案例，使用 Claude Code 辅助结构优化与文字润色。*
