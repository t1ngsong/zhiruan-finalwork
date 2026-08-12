"""CLI entry point and credential management for the Coding Agent Harness.

Provides AES-256-GCM encrypted API key storage and CLI subcommands:
  python -m agent run "task"   -- Run the agent
  python -m agent setup        -- Configure API key
  python -m agent status       -- View credential status
  python -m agent clear        -- Remove stored credentials
"""

import os
import sys
import argparse
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from agent.config.loader import ConfigLoader
from agent.llm.deepseek import DeepSeekAdapter
from agent.parser import ActionParser
from agent.tools import register_all_tools
from agent.tools.registry import ToolRegistry
from agent.tools.executor import ToolExecutor
from agent.guardrails.scorer import RiskScorer
from agent.guardrails.hitl import HITLGate
from agent.guardrails.fence import ScopeFence
from agent.guardrails.coordinator import GuardrailCoordinator
from agent.feedback.collector import FeedbackCollector
from agent.memory.store import MemoryStore
from agent.loop import AgentLoop


# ── Credential management ──────────────────────────────────────────────────────

def _get_secrets_file() -> Path:
    return Path(".agent") / "secrets.enc"


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
    return kdf.derive(password.encode("utf-8"))


def _encrypt(plaintext: str, password: str) -> bytes:
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return salt + nonce + ciphertext


def _decrypt(data: bytes, password: str) -> str:
    salt = data[:16]
    nonce = data[16:28]
    ciphertext = data[28:]
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def setup_credentials():
    """隐藏输入 API Key 并加密存储"""
    print("设置 Coding Agent 凭据")
    print("=" * 40)
    api_key = input("请输入 DeepSeek API Key: ")
    password = input("请设置主密码（用于加密存储 key）: ")
    confirm = input("请确认主密码: ")
    if password != confirm:
        print("❌ 密码不一致")
        sys.exit(1)

    encrypted = _encrypt(api_key, password)
    secrets_file = _get_secrets_file()
    secrets_file.parent.mkdir(parents=True, exist_ok=True)
    secrets_file.write_bytes(encrypted)
    print("✅ API Key 已安全存储")


def load_credentials() -> str:
    """加载并解密 API Key"""
    secrets_file = _get_secrets_file()
    if not secrets_file.exists():
        print("未配置 API Key。请先运行: python -m agent setup")
        sys.exit(1)
    password = input("请输入主密码以解锁 API Key: ")
    try:
        data = secrets_file.read_bytes()
        return _decrypt(data, password)
    except Exception:
        print("❌ 密码错误或数据损坏")
        sys.exit(1)


def show_status():
    """查看凭据状态（不回显明文）"""
    secrets_file = _get_secrets_file()
    if secrets_file.exists():
        print("API Key: 已配置 ✅")
    else:
        print("API Key: 未配置 ❌ 请运行: python -m agent setup")


def clear_credentials():
    secrets_file = _get_secrets_file()
    if secrets_file.exists():
        secrets_file.unlink()
        print("✅ 已清除凭据")
    else:
        print("无凭据可清除")


# ── Agent assembly ─────────────────────────────────────────────────────────────

def build_agent(config, api_key: str):
    """组装完整的 Agent"""
    workspace = Path(config.workspace).resolve()

    # 工具注册
    registry = ToolRegistry()
    register_all_tools(registry, workspace,
                       file_tools_enabled=config.file_tools_enabled,
                       shell_enabled=config.shell_enabled,
                       search_enabled=config.search_enabled,
                       shell_timeout=config.shell_timeout)

    # LLM
    llm = DeepSeekAdapter(api_key=api_key, model=config.model)
    llm.set_tool_schemas(registry.get_schemas_for_llm())

    # 护栏
    scorer = RiskScorer(workspace=workspace, custom_patterns=config.custom_patterns)
    hitl = HITLGate(timeout=config.hitl_timeout)
    fence = ScopeFence(workspace=workspace)
    guardrail = GuardrailCoordinator(scorer, hitl, fence)

    # 组件
    parser = ActionParser()
    executor = ToolExecutor(registry, workspace=workspace)
    feedback_collector = FeedbackCollector()
    memory = MemoryStore(workspace)

    return AgentLoop(config, llm, parser, registry, executor, guardrail, feedback_collector, memory)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Coding Agent Harness")
    subparsers = parser.add_subparsers(dest="command")

    # subcommand: run
    run_parser = subparsers.add_parser("run", help="运行 Agent")
    run_parser.add_argument("task", help="任务描述")
    run_parser.add_argument("--max-rounds", type=int, help="最大轮数")
    run_parser.add_argument("--model", help="模型名称")
    run_parser.add_argument("--workspace", help="工作目录")

    # subcommand: setup
    subparsers.add_parser("setup", help="配置 API Key")
    subparsers.add_parser("status", help="查看状态")
    subparsers.add_parser("clear", help="清除凭据")

    args = parser.parse_args()

    if args.command == "setup":
        setup_credentials()
    elif args.command == "status":
        show_status()
    elif args.command == "clear":
        clear_credentials()
    elif args.command == "run":
        config = ConfigLoader.load(".agent.yaml", cli_args=args)
        api_key = load_credentials()
        agent = build_agent(config, api_key)
        result = agent.run(args.task)
        print(f"\n{'='*40}")
        print(f"结果: {'✅ 成功' if result.success else '❌ 失败'}")
        print(f"轮次: {result.rounds}")
        print(f"摘要: {result.summary}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
