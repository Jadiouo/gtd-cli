from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from task import Task
from storage import TaskStorage


class TaskManager:
    def __init__(self, storage: TaskStorage):
        self.storage = storage

    def add_task(self, title: str, project: Optional[str] = None, priority: int = 3) -> Task:
        if not title or not title.strip():
            raise ValueError("--title is required")
        if not isinstance(priority, int) or priority < 1 or priority > 5:
            raise ValueError("Priority must be between 1 and 5")
        tasks = self.storage.load_tasks()
        next_id = self.storage.get_next_id()
        task = Task(id=next_id, title=title.strip(), project=project, priority=priority, status="inbox")
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

        tasks.sort(key=lambda t: (-t.priority, t.id))
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

    def show_task(self, task_id: int) -> Task:
        tasks = self.storage.load_tasks()
        task = next((t for t in tasks if t.id == task_id), None)
        if task is None:
            raise ValueError(f"Task [{task_id}] not found")
        return task
