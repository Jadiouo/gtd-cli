from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

VALID_STATUSES = ["inbox", "next-action", "waiting", "done"]
CONTEXT_RE = re.compile(r"^@[\w-]+$")


def normalize_context(value: Optional[str]) -> Optional[str]:
    """Contexts are GTD-style '@home', '@office', '@phone'. A leading '@' is added if missing."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not value.startswith("@"):
        value = "@" + value
    if not CONTEXT_RE.match(value):
        raise ValueError("Context must look like @home / @office (letters, digits, - and _)")
    return value.lower()


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
        due_date: Optional[date] = None,
        context: Optional[str] = None,
    ):
        self.id = id
        self.title = title
        self.project = project
        self.priority = priority
        self.status = status
        self.created_at = created_at if created_at is not None else datetime.now()
        self.updated_at = updated_at if updated_at is not None else datetime.now()
        self.due_date = due_date
        self.context = normalize_context(context)
        self.validate()

    def validate(self) -> bool:
        if not self.title or not self.title.strip():
            raise ValueError("Title cannot be empty")
        if not isinstance(self.priority, int) or self.priority < 1 or self.priority > 5:
            raise ValueError("Priority must be between 1 and 5")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Valid values are: {', '.join(VALID_STATUSES)}")
        if self.due_date is not None and not isinstance(self.due_date, date):
            raise ValueError("Invalid date format. Expected YYYY-MM-DD")
        if self.context is not None and not CONTEXT_RE.match(self.context):
            raise ValueError("Context must look like @home / @office")
        return True

    def is_overdue(self, today: Optional[date] = None) -> bool:
        today = today or date.today()
        return self.due_date is not None and self.due_date < today and self.status != "done"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "project": self.project,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "context": self.context,
        }

    @staticmethod
    def from_dict(data: dict) -> "Task":
        """Build a Task from stored JSON. Fields added in later versions (due_date, context) are optional."""
        due = data.get("due_date")
        return Task(
            id=data["id"],
            title=data["title"],
            project=data.get("project"),
            priority=data.get("priority", 3),
            status=data.get("status", "inbox"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            due_date=date.fromisoformat(due) if due else None,
            context=data.get("context"),
        )
