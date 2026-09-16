import sys
import os
import io

sys.path.insert(0, os.path.dirname(__file__))

import click
from datetime import date
from storage import TaskStorage
from commands import TaskManager

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

storage = TaskStorage()
manager = TaskManager(storage)


def parse_date(date_str: str) -> date:
    """Parse a YYYY-MM-DD date string. Raises ValueError on invalid format."""
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        raise ValueError("Invalid date format. Expected YYYY-MM-DD")


@click.group()
def cli():
    """GTD Task Manager - Getting Things Done CLI"""
    pass


@cli.command()
@click.option("--title", default=None, help="Task title")
@click.option("--project", default=None, help="Project name")
@click.option("--priority", default=3, type=int, help="Priority 1-5 (default: 3)")
@click.option("--due", default=None, help="Due date (YYYY-MM-DD)")
def add(title, project, priority, due):
    """Add a new task"""
    if not title:
        click.echo("❌ Error: --title is required", err=True)
        sys.exit(2)
    try:
        due_date = None
        if due is not None:
            due_date = parse_date(due)
        task = manager.add_task(title=title, project=project, priority=priority, due_date=due_date)
        proj_str = f"Project: {task.project}, " if task.project else ""
        due_str = f", Due: {task.due_date.isoformat()}" if task.due_date else ""
        click.echo(f"✅ Added: [{task.id}] {task.title} ({proj_str}Priority: {task.priority}{due_str})")
    except ValueError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(2)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command(name="list")
@click.option("--status", default=None, help="Filter by status")
@click.option("--project", default=None, help="Filter by project")
@click.option("--priority", default=None, type=int, help="Filter by priority")
@click.option("--all", "all_statuses", is_flag=True, default=False, help="Show all tasks including done")
@click.option("--due-before", default=None, help="Filter tasks due on or before DATE (YYYY-MM-DD)")
def list_tasks(status, project, priority, all_statuses, due_before):
    """List tasks"""
    try:
        due_before_date = None
        if due_before is not None:
            due_before_date = parse_date(due_before)

        tasks = manager.list_tasks(
            status=status,
            project=project,
            priority=priority,
            all_statuses=all_statuses,
            due_before=due_before_date,
        )
        if not tasks:
            click.echo("No tasks found.")
            return

        today = date.today()

        header = f"{'ID':<4} | {'Title':<22} | {'Project':<12} | {'Priority':<8} | {'Due':<12} | {'Status':<12} | {'Created'}"
        separator = (
            "-" * 4 + "-+-"
            + "-" * 22 + "-+-"
            + "-" * 12 + "-+-"
            + "-" * 8 + "-+-"
            + "-" * 12 + "-+-"
            + "-" * 12 + "-+-"
            + "-" * 10
        )
        click.echo(header)
        click.echo(separator)
        for task in tasks:
            proj = task.project if task.project else "(none)"
            created = task.created_at.strftime("%Y-%m-%d")

            # Due date display with overdue warning
            if task.due_date is not None:
                is_overdue = task.due_date < today and task.status != "done"
                due_str = task.due_date.isoformat()
                if is_overdue:
                    due_str = f"⚠️ {due_str}"
            else:
                due_str = "(none)"

            click.echo(
                f"{task.id:<4} | {task.title:<22} | {proj:<12} | {task.priority:<8} | {due_str:<12} | {task.status:<12} | {created}"
            )
    except ValueError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(2)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--id", "task_id", required=True, type=int, help="Task ID")
@click.option("--title", default=None, help="New title")
@click.option("--project", default=None, help="New project")
@click.option("--no-project", "clear_project", is_flag=True, default=False, help="Clear project association")
@click.option("--priority", default=None, type=int, help="New priority")
@click.option("--status", default=None, help="New status")
@click.option("--due", default=None, help="New due date (YYYY-MM-DD)")
@click.option("--no-due", "clear_due", is_flag=True, default=False, help="Clear due date")
def update(task_id, title, project, clear_project, priority, status, due, clear_due):
    """Update a task"""
    if due is not None and clear_due:
        click.echo("❌ Error: Cannot specify both --due and --no-due", err=True)
        sys.exit(2)

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
            click.echo(f"❌ Error: {str(e)}", err=True)
            sys.exit(2)

    try:
        task = manager.update_task(task_id, **kwargs)
        click.echo(f"✅ Updated: [{task.id}] {task.title}")
    except ValueError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--id", "task_id", required=True, type=int, help="Task ID")
def check(task_id):
    """Mark a task as done"""
    try:
        task = manager.check_task(task_id)
        click.echo(f"✅ Completed: [{task.id}] {task.title}")
    except ValueError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--id", "task_ids", required=True, type=int, multiple=True, help="Task ID(s) to remove")
@click.option("--force", is_flag=True, default=False, help="Skip confirmation")
def remove(task_ids, force):
    """Remove task(s)"""
    try:
        tasks = manager.storage.load_tasks()
        existing_ids = {t.id for t in tasks}

        not_found = [tid for tid in task_ids if tid not in existing_ids]
        found = [tid for tid in task_ids if tid in existing_ids]

        # Report not-found IDs
        for tid in not_found:
            click.echo(f"⚠️ ID {tid} not found.")

        if not_found and found and not force:
            # Ask user whether to continue with the existing ones
            answer = click.prompt(
                f"Some IDs not found. Continue deleting existing IDs {found}? (y/n)",
                type=str,
                default="n",
            )
            if answer.lower() != "y":
                click.echo("❌ Cancelled. No tasks were deleted.")
                return

        if not found:
            if not_found:
                click.echo("❌ Cancelled. No tasks were deleted.")
            return

        if not force:
            # Show deletion list and ask for confirmation
            click.echo("The following tasks will be deleted:")
            for tid in found:
                task = next((t for t in tasks if t.id == tid), None)
                if task:
                    click.echo(f"  [{task.id}] {task.title}")
            answer = click.prompt("Confirm deletion? (y/n)", type=str, default="n")
            if answer.lower() != "y":
                click.echo("❌ Cancelled. No tasks were deleted.")
                return

        # Perform deletion
        removed, failed, nf = manager.remove_tasks(found, force=True)

        # Output results
        parts = []
        if removed:
            removed_str = ", ".join(f"[{tid}]" for tid in removed)
            parts.append(f"✅ Removed: {removed_str}")
        if not_found:
            skipped_str = ", ".join(f"[{tid}]" for tid in not_found)
            parts.append(f"⚠️ Skipped: {skipped_str} (not found)")
        click.echo(" / ".join(parts) if parts else "No changes made.")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--id", "task_id", required=True, type=int, help="Task ID")
def show(task_id):
    """Show task details"""
    try:
        task = manager.show_task(task_id)
        proj = task.project if task.project else "(none)"
        due = task.due_date.isoformat() if task.due_date else "(none)"
        click.echo(f"Task [{task.id}]:")
        click.echo(f"  Title:     {task.title}")
        click.echo(f"  Project:   {proj}")
        click.echo(f"  Priority:  {task.priority}")
        click.echo(f"  Status:    {task.status}")
        click.echo(f"  Due:       {due}")
        click.echo(f"  Created:   {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        click.echo(f"  Updated:   {task.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    except ValueError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--project", default=None, help="Filter report by project")
def report(project):
    """Generate a statistics report"""
    try:
        tasks = manager.storage.load_tasks()
        report_str = manager.generate_report(tasks, project=project)
        click.echo(report_str)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
