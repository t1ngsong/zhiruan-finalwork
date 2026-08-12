# tests/config/test_loader.py
import tempfile
from pathlib import Path
from argparse import Namespace
import pytest
from agent.config.loader import ConfigLoader, Config


@pytest.fixture
def sample_yaml():
    return """
model: deepseek-chat
max_rounds: 20
workspace: "./project"

tools:
  shell:
    enabled: true
    timeout: 30

guardrails:
  hitl_timeout: 60

feedback:
  test_command: "pytest"
"""


def test_load_defaults():
    """不提供配置文件时使用默认值"""
    loader = ConfigLoader()
    config = loader.load(config_path=None, cli_args=None)
    assert config.model == "deepseek-chat"
    assert config.max_rounds == 20
    assert config.workspace == "."
    assert config.shell_timeout == 30


def test_load_from_file(tmp_path):
    """从 YAML 文件加载配置"""
    yaml_file = tmp_path / ".agent.yaml"
    yaml_file.write_text("""
model: deepseek-coder
max_rounds: 10
""")
    loader = ConfigLoader()
    config = loader.load(config_path=str(yaml_file), cli_args=None)
    assert config.model == "deepseek-coder"
    assert config.max_rounds == 10


def test_cli_overrides_config(tmp_path):
    """CLI 参数覆盖配置文件"""
    yaml_file = tmp_path / ".agent.yaml"
    yaml_file.write_text("model: deepseek-chat\nmax_rounds: 20\n")
    loader = ConfigLoader()
    cli_args = Namespace(max_rounds=5, model=None)
    config = loader.load(config_path=str(yaml_file), cli_args=cli_args)
    assert config.max_rounds == 5       # CLI 覆盖
    assert config.model == "deepseek-chat"  # 配置文件


def test_cli_overrides_default():
    """CLI 参数覆盖默认值（无配置文件）"""
    loader = ConfigLoader()
    cli_args = Namespace(max_rounds=5, model=None)
    config = loader.load(config_path=None, cli_args=cli_args)
    assert config.max_rounds == 5
