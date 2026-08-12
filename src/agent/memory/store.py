import json
import yaml
from pathlib import Path
from datetime import datetime


class MemoryStore:
    def __init__(self, project_root: Path):
        self.agent_dir = Path(project_root) / ".agent"
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        self.rules_file = self.agent_dir / "rules.yaml"
        self.decisions_file = self.agent_dir / "decisions.jsonl"

    def get_rules(self) -> str:
        if not self.rules_file.exists():
            return ""
        data = yaml.safe_load(self.rules_file.read_text(encoding="utf-8")) or {}
        lines = []
        for key, value in data.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def set_rule(self, key: str, value: str):
        data = {}
        if self.rules_file.exists():
            data = yaml.safe_load(self.rules_file.read_text(encoding="utf-8")) or {}
        data[key] = value
        self.rules_file.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

    def record_decision(self, action_summary: str, result_summary: str, approved: bool | None = None):
        decision = {
            "timestamp": datetime.now().isoformat(),
            "action_summary": action_summary,
            "result_summary": result_summary,
            "approved": approved,
        }
        with open(self.decisions_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision, ensure_ascii=False) + "\n")

    def get_recent_decisions(self, n: int = 10) -> list[dict]:
        if not self.decisions_file.exists():
            return []
        decisions = []
        with open(self.decisions_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    decisions.append(json.loads(line))
        return decisions[-n:]
