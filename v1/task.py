from __future__ import annotations
from datetime import datetime
from typing import Optional


VALID_STATUSES = ["inbox", "next-action", "waiting", "done"]


class Task:
    def __init__(
        self,
        id: int,
        title: str,
        project: Optional[str] = None,
        priority: int = 3,
        status: str = "inbox",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.title = title
        self.project = project
        self.priority = priority
        self.status = status
        self.created_at = created_at if created_at is not None else datetime.now()
        self.updated_at = updated_at if updated_at is not None else datetime.now()
        self.validate()

    def validate(self) -> bool:
        if not self.title or not self.title.strip():
            raise ValueError("Title cannot be empty")
        if not isinstance(self.priority, int) or self.priority < 1 or self.priority > 5:
            raise ValueError("Priority must be between 1 and 5")
        if self.status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status. Valid values are: {', '.join(VALID_STATUSES)}"
            )
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "project": self.project,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict) -> "Task":
        task = Task.__new__(Task)
        task.id = data["id"]
        task.title = data["title"]
        task.project = data.get("project")
        task.priority = data.get("priority", 3)
        task.status = data.get("status", "inbox")
        task.created_at = datetime.fromisoformat(data["created_at"])
        task.updated_at = datetime.fromisoformat(data["updated_at"])
        task.validate()
        return task
