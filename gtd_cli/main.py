"""gtd - a small Getting-Things-Done task manager for the terminal."""
from __future__ import annotations

import io
import sys
from datetime import date
from typing import Optional

import click

from . import __version__
from .commands import TaskManager
from .storage import TaskStorage

# Ensure UTF-8 output on Windows consoles (emoji in messages)
for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name)
    if getattr(stream, "encoding", "utf-8").lower() != "utf-8" and hasattr(stream, "buffer"):
        setattr(sys, stream_name, io.TextIOWrapper(stream.buffer, encoding="utf-8"))


def parse_date(date_str: str) -> date:
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        raise ValueError("Invalid date format. Expected YYYY-MM-DD")


def fail(message: str, code: int = 1) -> None:
    click.echo(f"❌ Error: {message}", err=True)
    sys.exit(code)


def get_manager(ctx: click.Context) -> TaskManager:
    return ctx.obj["manager"]


@click.group()
@click.version_option(__version__, prog_name="gtd")
@click.option("--file", "filepath", default=None, metavar="PATH",
              help="Task file (default: $GTD_FILE or ~/.gtd/tasks.json)")
@click.pass_context
def cli(ctx: click.Context, filepath: Optional[str]) -> None:
    """GTD Task Manager - Getting Things Done CLI.

    Capture everything into the inbox, decide what the next action is, tag it
    with a context (@home, @office, ...), and run `gtd review` once a week.
    """
    ctx.ensure_object(dict)
    ctx.obj["manager"] = TaskManager(TaskStorage(filepath))


# ------------------------------------------------------------------ add
@cli.command()
@click.option("--title", default=None, help="Task title")
@click.option("--project", default=None, help="Project name")
@click.option("--priority", default=3, type=int, help="Priority 1-5 (default: 3)")
@click.option("--due", default=None, help="Due date (YYYY-MM-DD)")
@click.option("--context", default=None, help="GTD context, e.g. @home, @office, @phone")
@click.pass_context
def add(ctx, title, project, priority, due, context):
    """Add a new task to the inbox"""
    if not title:
        fail("--title is required", 2)
    try:
        due_date = parse_date(due) if due is not None else None
        task = get_manager(ctx).add_task(title=title, project=project, priority=priority,
                                         due_date=due_date, context=context)
    except ValueError as e:
        fail(str(e), 2)
    proj_str = f"Project: {task.project}, " if task.project else ""
    due_str = f", Due: {task.due_date.isoformat()}" if task.due_date else ""
    ctx_str = f", Context: {task.context}" if task.context else ""
    click.echo(f"✅ Added: [{task.id}] {task.title} ({proj_str}Priority: {task.priority}{due_str}{ctx_str})")


# ------------------------------------------------------------------ list / next
def print_table(tasks) -> None:
    today = date.today()
    header = (f"{'ID':<4} | {'Title':<22} | {'Project':<12} | {'Ctx':<8} | {'Pri':<3} | "
              f"{'Due':<12} | {'Status':<12} | {'Created'}")
    click.echo(header)
    click.echo("-" * len(header))
    for task in tasks:
        proj = task.project or "(none)"
        ctxs = task.context or "-"
        if task.due_date is not None:
            due_str = task.due_date.isoformat()
            if task.is_overdue(today):
                due_str = f"⚠️ {due_str}"
        else:
            due_str = "(none)"
        click.echo(f"{task.id:<4} | {task.title:<22} | {proj:<12} | {ctxs:<8} | {task.priority:<3} | "
                   f"{due_str:<12} | {task.status:<12} | {task.created_at.strftime('%Y-%m-%d')}")


@cli.command(name="list")
@click.option("--status", default=None, help="Filter by status")
@click.option("--project", default=None, help="Filter by project")
@click.option("--priority", default=None, type=int, help="Filter by priority")
@click.option("--context", default=None, help="Filter by context (@home, ...)")
@click.option("--all", "all_statuses", is_flag=True, default=False, help="Show all tasks including done")
@click.option("--due-before", default=None, help="Filter tasks due on or before DATE (YYYY-MM-DD)")
@click.pass_context
def list_tasks(ctx, status, project, priority, context, all_statuses, due_before):
    """List tasks (default: inbox + next-action)"""
    try:
        due_before_date = parse_date(due_before) if due_before is not None else None
        tasks = get_manager(ctx).list_tasks(status=status, project=project, priority=priority,
                                            all_statuses=all_statuses, due_before=due_before_date,
                                            context=context)
    except ValueError as e:
        fail(str(e), 2)
    if not tasks:
        click.echo("No tasks found.")
        return
    print_table(tasks)


@cli.command(name="next")
@click.option("--context", default=None, help="Only next actions doable in this context")
@click.option("--project", default=None, help="Only next actions of this project")
@click.pass_context
def next_actions(ctx, context, project):
    """Show the next-action list, optionally for one context"""
    try:
        tasks = get_manager(ctx).next_actions(context=context, project=project)
    except ValueError as e:
        fail(str(e), 2)
    if not tasks:
        where = f" in {context}" if context else ""
        click.echo(f"No next actions{where}. Process your inbox: gtd list --status inbox")
        return
    print_table(tasks)


# ------------------------------------------------------------------ update / check
@cli.command()
@click.option("--id", "task_id", required=True, type=int, help="Task ID")
@click.option("--title", default=None, help="New title")
@click.option("--project", default=None, help="New project")
@click.option("--no-project", "clear_project", is_flag=True, default=False, help="Clear project association")
@click.option("--priority", default=None, type=int, help="New priority")
@click.option("--status", default=None, help="New status (inbox, next-action, waiting, done)")
@click.option("--due", default=None, help="New due date (YYYY-MM-DD)")
@click.option("--no-due", "clear_due", is_flag=True, default=False, help="Clear due date")
@click.option("--context", default=None, help="New context (@home, ...)")
@click.option("--no-context", "clear_context", is_flag=True, default=False, help="Clear context")
@click.pass_context
def update(ctx, task_id, title, project, clear_project, priority, status, due, clear_due, context, clear_context):
    """Update a task"""
    if due is not None and clear_due:
        fail("Cannot specify both --due and --no-due", 2)
    if context is not None and clear_context:
        fail("Cannot specify both --context and --no-context", 2)

    kwargs = {}
    if title is not None:
        kwargs["title"] = title
    if clear_project:
        kwargs["project"] = ""
    elif project is not None:
        kwargs["project"] = project
    if priority is not None:
        kwargs["priority"] = priority
    if status is not None:
        kwargs["status"] = status
    if clear_due:
        kwargs["due_date"] = None
    elif due is not None:
        try:
            kwargs["due_date"] = parse_date(due)
        except ValueError as e:
            fail(str(e), 2)
    if clear_context:
        kwargs["context"] = None
    elif context is not None:
        kwargs["context"] = context

    try:
        task = get_manager(ctx).update_task(task_id, **kwargs)
    except ValueError as e:
        fail(str(e), 1)
    click.echo(f"✅ Updated: [{task.id}] {task.title}")


@cli.command()
@click.option("--id", "task_id", required=True, type=int, help="Task ID")
@click.pass_context
def check(ctx, task_id):
    """Mark a task as done"""
    try:
        task = get_manager(ctx).check_task(task_id)
    except ValueError as e:
        fail(str(e), 1)
    click.echo(f"✅ Completed: [{task.id}] {task.title}")


# ------------------------------------------------------------------ remove / undo
@cli.command()
@click.option("--id", "task_ids", required=True, type=int, multiple=True, help="Task ID(s) to remove")
@click.option("--force", is_flag=True, default=False, help="Skip confirmation")
@click.pass_context
def remove(ctx, task_ids, force):
    """Remove task(s); the previous file is kept as a backup (see `gtd undo`)"""
    manager = get_manager(ctx)
    tasks = manager.storage.load_tasks()
    existing_ids = {t.id for t in tasks}
    not_found = [tid for tid in task_ids if tid not in existing_ids]
    found = [tid for tid in task_ids if tid in existing_ids]

    for tid in not_found:
        click.echo(f"⚠️ ID {tid} not found.")

    if not_found and found and not force:
        answer = click.prompt(f"Some IDs not found. Continue deleting existing IDs {found}? (y/n)",
                              type=str, default="n")
        if answer.lower() != "y":
            click.echo("❌ Cancelled. No tasks were deleted.")
            return

    if not found:
        if not_found:
            click.echo("❌ Cancelled. No tasks were deleted.")
        return

    if not force:
        click.echo("The following tasks will be deleted:")
        for tid in found:
            task = next(t for t in tasks if t.id == tid)
            click.echo(f"  [{task.id}] {task.title}")
        answer = click.prompt("Confirm deletion? (y/n)", type=str, default="n")
        if answer.lower() != "y":
            click.echo("❌ Cancelled. No tasks were deleted.")
            return

    removed, _, _ = manager.remove_tasks(found, force=True)
    parts = []
    if removed:
        parts.append("✅ Removed: " + ", ".join(f"[{tid}]" for tid in removed))
    if not_found:
        parts.append("⚠️ Skipped: " + ", ".join(f"[{tid}]" for tid in not_found) + " (not found)")
    click.echo(" / ".join(parts) if parts else "No changes made.")


@cli.command()
@click.pass_context
def undo(ctx):
    """Restore the task file from the backup written before the last change"""
    storage = get_manager(ctx).storage
    if storage.restore_backup():
        click.echo(f"✅ Restored {storage.filepath} from {storage.backup_path}")
    else:
        fail("No backup found", 1)


# ------------------------------------------------------------------ show / report / review
@cli.command()
@click.option("--id", "task_id", required=True, type=int, help="Task ID")
@click.pass_context
def show(ctx, task_id):
    """Show task details"""
    try:
        task = get_manager(ctx).show_task(task_id)
    except ValueError as e:
        fail(str(e), 1)
    click.echo(f"Task [{task.id}]:")
    click.echo(f"  Title:     {task.title}")
    click.echo(f"  Project:   {task.project or '(none)'}")
    click.echo(f"  Context:   {task.context or '(none)'}")
    click.echo(f"  Priority:  {task.priority}")
    click.echo(f"  Status:    {task.status}")
    click.echo(f"  Due:       {task.due_date.isoformat() if task.due_date else '(none)'}")
    click.echo(f"  Created:   {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"  Updated:   {task.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")


@cli.command()
@click.option("--project", default=None, help="Filter report by project")
@click.pass_context
def report(ctx, project):
    """Statistics: status counts, project distribution, overdue alert"""
    manager = get_manager(ctx)
    click.echo(manager.generate_report(manager.storage.load_tasks(), project=project))


@cli.command()
@click.pass_context
def review(ctx):
    """Weekly review: overdue, due soon, inbox to process, waiting-for, stale, done this week"""
    click.echo(get_manager(ctx).format_weekly_review())


if __name__ == "__main__":
    cli()
