# src/agent/config/loader.py
from dataclasses import dataclass, field
from pathlib import Path
from argparse import Namespace
import yaml


@dataclass
class Config:
    model: str = "deepseek-chat"
    max_rounds: int = 20
    workspace: str = "."
    shell_timeout: int = 30
    file_tools_enabled: bool = True
    search_enabled: bool = True
    shell_enabled: bool = True
    hitl_timeout: int = 60
    test_command: str = "pytest"
    lint_command: str = "ruff check ."
    type_check_command: str = "mypy ."
    custom_patterns: list = field(default_factory=list)


class ConfigLoader:
    @staticmethod
    def load(config_path: str | None = None, cli_args: Namespace | None = None) -> Config:
        config = Config()

        # 1. 加载 YAML 配置文件
        if config_path:
            path = Path(config_path)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                config = ConfigLoader._apply_yaml(config, data)

        # 2. CLI 覆盖
        if cli_args:
            for key in ["model", "max_rounds", "workspace"]:
                val = getattr(cli_args, key, None)
                if val is not None:
                    setattr(config, key, val)

        return config

    @staticmethod
    def _apply_yaml(config: Config, data: dict) -> Config:
        if "model" in data:
            config.model = data["model"]
        if "max_rounds" in data:
            config.max_rounds = data["max_rounds"]
        if "workspace" in data:
            config.workspace = data["workspace"]

        tools = data.get("tools", {})
        shell = tools.get("shell", {})
        if "timeout" in shell:
            config.shell_timeout = shell["timeout"]
        if "enabled" in shell:
            config.shell_enabled = shell["enabled"]

        file_tools = tools.get("file", {})
        if "enabled" in file_tools:
            config.file_tools_enabled = file_tools["enabled"]

        search = tools.get("search", {})
        if "enabled" in search:
            config.search_enabled = search["enabled"]

        guardrails = data.get("guardrails", {})
        if "hitl_timeout" in guardrails:
            config.hitl_timeout = guardrails["hitl_timeout"]
        if "custom_patterns" in guardrails:
            config.custom_patterns = guardrails["custom_patterns"]

        feedback = data.get("feedback", {})
        if "test_command" in feedback:
            config.test_command = feedback["test_command"]
        if "lint_command" in feedback:
            config.lint_command = feedback["lint_command"]
        if "type_check_command" in feedback:
            config.type_check_command = feedback["type_check_command"]

        return config
