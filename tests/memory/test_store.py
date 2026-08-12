import pytest
from pathlib import Path
from agent.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    return MemoryStore(tmp_path)


def test_default_rules_empty(store):
    assert store.get_rules() == ""


def test_set_and_get_rule(store):
    store.set_rule("code_style", "使用 snake_case")
    rules = store.get_rules()
    assert "code_style" in rules
    assert "snake_case" in rules


def test_record_and_get_decisions(store):
    store.record_decision("执行了 pytest", "3 passed, 1 failed", approved=True)
    store.record_decision("执行了 git push", "被护栏拦截", approved=False)
    decisions = store.get_recent_decisions(10)
    assert len(decisions) == 2
    assert decisions[0]["action_summary"] == "执行了 pytest"
    assert decisions[1]["approved"] is False


def test_get_recent_decisions_limited(store):
    for i in range(20):
        store.record_decision(f"action {i}", "ok", approved=True)
    decisions = store.get_recent_decisions(5)
    assert len(decisions) == 5


def test_rules_file_persisted(tmp_path):
    store = MemoryStore(tmp_path)
    store.set_rule("test_rule", "value")
    # 重新加载
    store2 = MemoryStore(tmp_path)
    assert "test_rule" in store2.get_rules()
