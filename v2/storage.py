from __future__ import annotations
import json
import os
from typing import List

from task import Task


class TaskStorage:
    def __init__(self, filepath: str = None):
        if filepath is None:
            home = os.path.expanduser("~")
            filepath = os.path.join(home, ".gtd", "tasks.json")
        self.filepath = filepath
        self._ensure_directory()
        self._ensure_file()

    def _ensure_directory(self):
        directory = os.path.dirname(self.filepath)
        os.makedirs(directory, exist_ok=True)

    def _ensure_file(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({"tasks": [], "next_id": 1}, f, indent=2)

    def load_tasks(self) -> List[Task]:
        """Load tasks from JSON file. Backward compatible with v1 format (missing due_date)."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse tasks file: {e}")
        return [Task.from_dict(t) for t in data.get("tasks", [])]

    def save_tasks(self, tasks: List[Task]):
        """Save tasks to JSON file, including due_date field."""
        next_id = max((t.id for t in tasks), default=0) + 1
        data = {
            "tasks": [t.to_dict() for t in tasks],
            "next_id": next_id,
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_next_id(self) -> int:
        with open(self.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("next_id", 1)
