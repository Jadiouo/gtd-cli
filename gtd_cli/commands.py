from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from .report import format_report, format_review
from .storage import TaskStorage
from .task import Task, normalize_context

STALE_AFTER_DAYS = 14


class TaskManager:
    def __init__(self, storage: TaskStorage):
        self.storage = storage

    # ------------------------------------------------------------------ CRUD
    def add_task(
        self,
        title: str,
        project: Optional[str] = None,
        priority: int = 3,
        due_date: Optional[date] = None,
        context: Optional[str] = None,
    ) -> Task:
        if not title or not title.strip():
            raise ValueError("--title is required")
        if not isinstance(priority, int) or priority < 1 or priority > 5:
            raise ValueError("Priority must be between 1 and 5")
        tasks = self.storage.load_tasks()
        task = Task(
            id=self.storage.get_next_id(),
            title=title.strip(),
            project=project.strip() if project else None,
            priority=priority,
            status="inbox",
            due_date=due_date,
            context=context,
        )
        tasks.append(task)
        self.storage.save_tasks(tasks)
        return task

    def list_tasks(
        self,
        status: Optional[str] = None,
        project: Optional[str] = None,
        priority: Optional[int] = None,
        all_statuses: bool = False,
        due_before: Optional[date] = None,
        context: Optional[str] = None,
    ) -> List[Task]:
        tasks = self.storage.load_tasks()

        if all_statuses:
            pass
        elif status is not None:
            tasks = [t for t in tasks if t.status == status]
        else:
            tasks = [t for t in tasks if t.status in ("inbox", "next-action")]

        if project is not None:
            tasks = [t for t in tasks if t.project == project]
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]
        if due_before is not None:
            tasks = [t for t in tasks if t.due_date is not None and t.due_date <= due_before]
        if context is not None:
            tasks = [t for t in tasks if t.context == normalize_context(context)]

        return sorted(tasks, key=self._sort_key)

    @staticmethod
    def _sort_key(t: Task):
        """Overdue first, then priority 5->1, then nearest due date, then id."""
        due_sort = t.due_date if t.due_date is not None else date.max
        return (not t.is_overdue(), -t.priority, due_sort, t.id)

    def next_actions(self, context: Optional[str] = None, project: Optional[str] = None) -> List[Task]:
        """The GTD 'next actions' list: what can be done right now, optionally in one context."""
        return self.list_tasks(status="next-action", project=project, context=context)

    def update_task(self, task_id: int, **kwargs) -> Task:
        tasks = self.storage.load_tasks()
        task = self._find(tasks, task_id)

        if "title" in kwargs:
            task.title = kwargs["title"].strip()
        if "project" in kwargs:
            val = kwargs["project"]
            task.project = val.strip() if val else None
        if "priority" in kwargs:
            task.priority = kwargs["priority"]
        if "status" in kwargs:
            task.status = kwargs["status"]
        if "due_date" in kwargs:
            task.due_date = kwargs["due_date"]
        if "context" in kwargs:
            task.context = normalize_context(kwargs["context"])

        task.validate()
        task.updated_at = datetime.now()
        self.storage.save_tasks(tasks)
        return task

    def check_task(self, task_id: int) -> Task:
        return self.update_task(task_id, status="done")

    def remove_task(self, task_id: int) -> None:
        tasks = self.storage.load_tasks()
        new_tasks = [t for t in tasks if t.id != task_id]
        if len(new_tasks) == len(tasks):
            raise ValueError(f"Task [{task_id}] not found")
        self.storage.save_tasks(new_tasks)

    def remove_tasks(self, task_ids: List[int], force: bool = False) -> Tuple[List[int], List[int], List[int]]:
        """Remove several tasks. Returns (removed_ids, failed_ids, not_found_ids)."""
        tasks = self.storage.load_tasks()
        existing = {t.id for t in tasks}
        not_found = [tid for tid in task_ids if tid not in existing]
        found = [tid for tid in task_ids if tid in existing]
        if not found:
            return ([], [], not_found)
        self.storage.save_tasks([t for t in tasks if t.id not in set(found)])
        return (found, [], not_found)

    def show_task(self, task_id: int) -> Task:
        return self._find(self.storage.load_tasks(), task_id)

    @staticmethod
    def _find(tasks: List[Task], task_id: int) -> Task:
        task = next((t for t in tasks if t.id == task_id), None)
        if task is None:
            raise ValueError(f"Task [{task_id}] not found")
        return task

    # --------------------------------------------------------------- reports
    def generate_report(self, tasks: List[Task], project: Optional[str] = None) -> str:
        return format_report(tasks, project)

    def get_overdue_tasks(self, tasks: List[Task]) -> List[Task]:
        return [t for t in tasks if t.is_overdue()]

    def weekly_review(self, today: Optional[date] = None, stale_days: int = STALE_AFTER_DAYS) -> dict:
        """Collect everything a GTD weekly review looks at."""
        today = today or date.today()
        tasks = self.storage.load_tasks()
        week_end = today + timedelta(days=7)
        week_start = today - timedelta(days=7)
        stale_cutoff = datetime.combine(today - timedelta(days=stale_days), datetime.min.time())
        open_tasks = [t for t in tasks if t.status != "done"]
        return {
            "today": today,
            "overdue": sorted((t for t in tasks if t.is_overdue(today)), key=self._sort_key),
            "due_this_week": sorted(
                (t for t in open_tasks if t.due_date is not None and today <= t.due_date <= week_end),
                key=lambda t: (t.due_date, -t.priority, t.id)),
            "inbox": [t for t in tasks if t.status == "inbox"],
            "waiting": [t for t in tasks if t.status == "waiting"],
            "stale": [t for t in open_tasks if t.updated_at < stale_cutoff],
            "done_this_week": [t for t in tasks if t.status == "done" and t.updated_at.date() >= week_start],
            "contexts": sorted({t.context for t in open_tasks if t.context}),
        }

    def format_weekly_review(self, today: Optional[date] = None) -> str:
        return format_review(self.weekly_review(today))
