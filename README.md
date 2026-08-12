# Coding Agent Harness

一个从零构建的透明、可定制、可独立验证的 Coding Agent Harness。

## 简介

本项目是 AI4SE 课程的期末项目（A 方向）。核心命题：**当 LLM 能完成大部分编码工作时，工程师的价值在哪里？** 答案在 Harness 层的工程机制——治理、反馈、上下文、安全、分发。

### 核心特性

- **自主编码**：接收任务描述 → 多轮工具调用 → 反馈驱动自我修正
- **四层治理护栏**：模式匹配 → 风险评分 → HITL 审批 → 范围围栏（重点维度）
- **确定性反馈闭环**：测试/lint/类型检查结果自动解析并回灌
- **Mock LLM**：替换真实 LLM 后所有核心机制可离线验证
- **凭据安全**：AES-256-GCM 加密存储，不回显，不硬编码

## 快速开始

### Docker（推荐）

```bash
# 构建
docker build -t coding-agent .

# 配置 API Key（首次运行）
docker run -it coding-agent setup

# 运行
docker run -it -v $(pwd):/workspace coding-agent run "你的编码任务"
```

### 本地开发

```bash
pip install -e ".[dev]"
python -m agent setup          # 配置 API Key
python -m agent status         # 查看状态
python -m agent run "任务描述"  # 运行 Agent
```

## 运行测试

```bash
pytest tests/ -v
```

所有核心机制测试使用 Mock LLM，不访问网络。

## 配置

编辑项目根目录的 `.agent.yaml`：

```yaml
model: deepseek-chat
max_rounds: 20
workspace: "."

tools:
  shell:
    enabled: true
    timeout: 30

guardrails:
  custom_patterns:
    - pattern: "rm -rf /tmp/myapp"
      level: low
      reason: "已确认安全的清理命令"
  hitl_timeout: 60

feedback:
  test_command: "pytest"
  lint_command: "ruff check ."
  type_check_command: "mypy ."
```

## 目录结构

```
src/agent/
├── main.py          # CLI 入口 + 凭据管理
├── loop.py          # Agent 主循环
├── parser.py        # 动作解析
├── context.py       # 上下文组装
├── stop_checker.py  # 停机判断
├── llm/             # LLM 抽象层 (DeepSeek + Mock)
├── tools/           # 工具系统 (Registry + Executor + 4 Tools)
├── guardrails/      # 治理护栏 (重点维度)
├── feedback/        # 反馈闭环 (4 解析器)
├── memory/          # 记忆系统
└── config/          # 配置系统
```

## 安全

- API Key 使用 AES-256-GCM 加密存储（PBKDF2 密钥派生）
- 绝不在源码、Git 历史、日志、终端输出中出现明文 Key
- 危险操作（rm -rf /、DROP TABLE 等）自动拦截
- 中高风险操作需人工审批

## 已知限制

- **平台**：开发和测试均在 Windows / Linux（CI Ubuntu）上通过，macOS 未经测试
- **架构**：仅支持 x86_64（Python 3.11+ 通用，但 Docker 镜像基于 linux/amd64）
- **依赖前提**：Docker 分发需 Docker Engine 20.10+；本地开发需 Python 3.11+ 及 pip
- **LLM 供应商**：当前仅适配 DeepSeek API（兼容 OpenAI SDK 接口），切换供应商需修改源码
- **护栏覆盖**：8 个内置危险模式覆盖常见场景，但已知 `rm -r -f /`（参数分开写）等变体未捕获
- **并发**：不支持多 Agent 并发运行，无会话隔离

## 许可

MIT

## 线上部署说明

本项目为纯 CLI / 纯后端项目，不包含 WebUI 界面。根据课程通用要求 §3.6 "纯 CLI / 纯后端项目可豁免" Open Design 与线上部署 URL 要求。分发方式为 Docker 容器镜像（见上方快速开始）。
