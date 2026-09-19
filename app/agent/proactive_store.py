import json
from pathlib import Path
from typing import Any, Dict, List


class ProactiveStore:
    def __init__(self, file_path: str = "data/proactive_tasks.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def save_tasks(self, tasks: List[Dict[str, Any]]):
        with self.file_path.open("w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)

    def load_tasks(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            return []

        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            return data if isinstance(data, list) else []

        except (json.JSONDecodeError, OSError):
            return []

    def clear(self):
        if self.file_path.exists():
            self.file_path.unlink()

    def exists(self) -> bool:
        return self.file_path.exists()