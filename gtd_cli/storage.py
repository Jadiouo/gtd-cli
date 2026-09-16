from __future__ import annotations

import json
import os
import shutil
from typing import List, Optional

from .task import Task

ENV_FILE = "GTD_FILE"


def default_path() -> str:
    """Task file location: $GTD_FILE if set, otherwise ~/.gtd/tasks.json."""
    env = os.environ.get(ENV_FILE)
    if env:
        return os.path.expanduser(env)
    return os.path.join(os.path.expanduser("~"), ".gtd", "tasks.json")


class TaskStorage:
    """JSON file storage: {"tasks": [...], "next_id": N}.

    Every save first copies the previous file to <file>.bak, so one mistaken
    `remove` can always be undone by restoring the backup.
    """

    def __init__(self, filepath: Optional[str] = None, backup: bool = True):
        self.filepath = filepath or default_path()
        self.backup = backup
        self._ensure_directory()
        self._ensure_file()

    @property
    def backup_path(self) -> str:
        return self.filepath + ".bak"

    def _ensure_directory(self) -> None:
        directory = os.path.dirname(self.filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _ensure_file(self) -> None:
        if not os.path.exists(self.filepath):
            self._write({"tasks": [], "next_id": 1})

    def _read(self) -> dict:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse tasks file {self.filepath}: {e}") from e

    def _write(self, data: dict) -> None:
        tmp = self.filepath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.filepath)          # atomic on POSIX and Windows

    def load_tasks(self) -> List[Task]:
        return [Task.from_dict(t) for t in self._read().get("tasks", [])]

    def save_tasks(self, tasks: List[Task]) -> None:
        if self.backup and os.path.exists(self.filepath):
            shutil.copyfile(self.filepath, self.backup_path)
        # next_id never reuses a deleted id, so keep the stored counter if it is larger
        stored_next = self._read().get("next_id", 1)
        next_id = max(stored_next, max((t.id for t in tasks), default=0) + 1)
        self._write({"tasks": [t.to_dict() for t in tasks], "next_id": next_id})

    def get_next_id(self) -> int:
        return self._read().get("next_id", 1)

    def restore_backup(self) -> bool:
        """Replace the task file with the last backup. Returns False if there is none."""
        if not os.path.exists(self.backup_path):
            return False
        shutil.copyfile(self.backup_path, self.filepath)
        return True
