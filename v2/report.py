from __future__ import annotations
from datetime import date
from typing import List, Optional

from task import Task


def format_report(tasks: List[Task], project: Optional[str] = None) -> str:
    """
    Generate a statistics report from the given task list.
    If project is specified, only tasks belonging to that project are included.
    """
    if project is not None:
        tasks = [t for t in tasks if t.project == project]

    lines: List[str] = []

    # === Inbox Status Overview ===
    status_counts = {
        "inbox": 0,
        "next-action": 0,
        "waiting": 0,
        "done": 0,
    }
    for t in tasks:
        if t.status in status_counts:
            status_counts[t.status] += 1

    total = len(tasks)

    lines.append("=== Inbox Status Overview ===")
    lines.append(f"inbox:       {status_counts['inbox']} tasks")
    lines.append(f"next-action: {status_counts['next-action']} tasks")
    lines.append(f"waiting:     {status_counts['waiting']} tasks")
    lines.append(f"done:        {status_counts['done']} tasks")
    lines.append(f"Total:       {total} tasks")
    lines.append("")

    # === Project Distribution ===
    lines.append("=== Project Distribution ===")
    project_map: dict[str, List[Task]] = {}
    for t in tasks:
        key = t.project if t.project else "(no project)"
        project_map.setdefault(key, []).append(t)

    for proj_name in sorted(project_map.keys()):
        proj_tasks = project_map[proj_name]
        lines.append(f"  {proj_name}:")
        p_counts = {"inbox": 0, "next-action": 0, "waiting": 0, "done": 0}
        for t in proj_tasks:
            if t.status in p_counts:
                p_counts[t.status] += 1
        for s_name, s_count in p_counts.items():
            if s_count > 0:
                lines.append(f"    {s_name}: {s_count}")
    lines.append("")

    # === Overdue Alert ===
    today = date.today()
    overdue = [
        t for t in tasks
        if t.due_date is not None and t.due_date < today and t.status != "done"
    ]
    lines.append("=== Overdue Alert ===")
    if overdue:
        lines.append(f"⚠️  {len(overdue)} overdue task(s):")
        for t in overdue:
            lines.append(f"  [{t.id}] {t.title} (due: {t.due_date.isoformat()})")
    else:
        lines.append("🎉 No overdue tasks! Keep up the great work!")

    return "\n".join(lines)
