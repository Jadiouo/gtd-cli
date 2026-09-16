from __future__ import annotations

from datetime import date
from typing import List, Optional

from .task import VALID_STATUSES, Task


def _task_line(t: Task, show_due: bool = True) -> str:
    bits = [f"[{t.id}] {t.title}"]
    if t.project:
        bits.append(f"({t.project})")
    if t.context:
        bits.append(t.context)
    if show_due and t.due_date:
        bits.append(f"due {t.due_date.isoformat()}")
    return "  " + " ".join(bits)


def format_report(tasks: List[Task], project: Optional[str] = None) -> str:
    """Overall status counts, per-project distribution and overdue alert."""
    if project is not None:
        tasks = [t for t in tasks if t.project == project]

    lines: List[str] = []
    status_counts = {s: 0 for s in VALID_STATUSES}
    for t in tasks:
        status_counts[t.status] += 1

    lines.append("=== Inbox Status Overview ===")
    lines.append(f"inbox:       {status_counts['inbox']} tasks")
    lines.append(f"next-action: {status_counts['next-action']} tasks")
    lines.append(f"waiting:     {status_counts['waiting']} tasks")
    lines.append(f"done:        {status_counts['done']} tasks")
    lines.append(f"Total:       {len(tasks)} tasks")
    lines.append("")

    lines.append("=== Project Distribution ===")
    project_map: dict[str, List[Task]] = {}
    for t in tasks:
        project_map.setdefault(t.project or "(no project)", []).append(t)
    for proj_name in sorted(project_map):
        lines.append(f"  {proj_name}:")
        counts = {s: 0 for s in VALID_STATUSES}
        for t in project_map[proj_name]:
            counts[t.status] += 1
        for s_name, s_count in counts.items():
            if s_count:
                lines.append(f"    {s_name}: {s_count}")
    lines.append("")

    overdue = [t for t in tasks if t.is_overdue()]
    lines.append("=== Overdue Alert ===")
    if overdue:
        lines.append(f"⚠️  {len(overdue)} overdue task(s):")
        for t in overdue:
            lines.append(f"  [{t.id}] {t.title} (due: {t.due_date.isoformat()})")
    else:
        lines.append("🎉 No overdue tasks! Keep up the great work!")
    return "\n".join(lines)


def format_review(r: dict) -> str:
    """Render the weekly-review dict from TaskManager.weekly_review()."""
    today: date = r["today"]
    lines = [f"=== Weekly Review — {today.isoformat()} ==="]

    def section(title: str, items: List[Task], empty: str, show_due: bool = True) -> None:
        lines.append("")
        lines.append(f"{title} ({len(items)})")
        if items:
            lines.extend(_task_line(t, show_due) for t in items)
        else:
            lines.append(f"  {empty}")

    section("⚠️  Overdue", r["overdue"], "nothing overdue")
    section("📅 Due in the next 7 days", r["due_this_week"], "nothing due this week")
    section("📥 Inbox to process (decide: next-action / waiting / done / remove)", r["inbox"],
            "inbox is empty", show_due=False)
    section("⏳ Waiting for", r["waiting"], "not waiting on anyone", show_due=False)
    section(f"🕸️  Stale (untouched for 14+ days)", r["stale"], "everything has been touched recently")
    section("✅ Completed in the last 7 days", r["done_this_week"], "nothing completed yet", show_due=False)

    lines.append("")
    if r["contexts"]:
        lines.append("Contexts in use: " + ", ".join(r["contexts"]))
    else:
        lines.append("Contexts in use: (none — try `gtd update --id N --context @home`)")
    return "\n".join(lines)
