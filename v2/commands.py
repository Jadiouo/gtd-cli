from __future__ import annotations
from datetime import date
from typing import List, Optional, Tuple

from report import format_report
from task import Task
from storage import TaskStorage


class TaskManager:
    def __init__(self, storage: TaskStorage):
        self.storage = storage

    def add_task(
        self,
        title: str,
        project: Optional[str] = None,
        priority: int = 3,
        due_date: Optional[date] = None,
    ) -> Task:
        if not title or not title.strip():
            raise ValueError("--title is required")
        if not isinstance(priority, int) or priority < 1 or priority > 5:
            raise ValueError("Priority must be between 1 and 5")
        tasks = self.storage.load_tasks()
        next_id = self.storage.get_next_id()
        task = Task(
            id=next_id,
            title=title.strip(),
            project=project,
            priority=priority,
            status="inbox",
            due_date=due_date,
        )
        task.validate()
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

        today = date.today()

        def sort_key(t: Task):
            # 1. Overdue first (due_date < today AND status != done)
            is_overdue = (
                t.due_date is not None
                and t.due_date < today
                and t.status != "done"
            )
            # 2. Priority descending (5→1)
            # 3. Due date ascending (nearest first, None at end)
            # 4. ID ascending
            due_sort = t.due_date if t.due_date is not None else date.max
            return (not is_overdue, -t.priority, due_sort, t.id)

        tasks.sort(key=sort_key)
        return tasks

    def update_task(self, task_id: int, **kwargs) -> Task:
        tasks = self.storage.load_tasks()
        task = next((t for t in tasks if t.id == task_id), None)
        if task is None:
            raise ValueError(f"Task [{task_id}] not found")

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

        task.validate()
        from datetime import datetime
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

    def remove_tasks(
        self, task_ids: List[int], force: bool = False
    ) -> Tuple[List[int], List[int], List[int]]:
        """
        Remove multiple tasks at once.
        Returns: (removed_ids, failed_ids, not_found_ids)
        """
        tasks = self.storage.load_tasks()
        existing_ids = {t.id for t in tasks}

        not_found_ids = [tid for tid in task_ids if tid not in existing_ids]
        found_ids = [tid for tid in task_ids if tid in existing_ids]

        if not found_ids:
            return ([], [], not_found_ids)

        # Remove found tasks
        new_tasks = [t for t in tasks if t.id not in set(found_ids)]
        self.storage.save_tasks(new_tasks)

        return (found_ids, [], not_found_ids)

    def show_task(self, task_id: int) -> Task:
        tasks = self.storage.load_tasks()
        task = next((t for t in tasks if t.id == task_id), None)
        if task is None:
            raise ValueError(f"Task [{task_id}] not found")
        return task

    def generate_report(
        self, tasks: List[Task], project: Optional[str] = None
    ) -> str:
        return format_report(tasks, project)

    def get_overdue_tasks(self, tasks: List[Task]) -> List[Task]:
        """Return tasks with due_date < today AND status != done."""
        today = date.today()
        return [
            t
            for t in tasks
            if t.due_date is not None and t.due_date < today and t.status != "done"
        ]
