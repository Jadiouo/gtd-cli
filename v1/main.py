import sys
import io
import click
from storage import TaskStorage
from commands import TaskManager

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

storage = TaskStorage()
manager = TaskManager(storage)


@click.group()
def cli():
    """GTD Task Manager - Getting Things Done CLI"""
    pass


@cli.command()
@click.option("--title", default=None, help="Task title")
@click.option("--project", default=None, help="Project name")
@click.option("--priority", default=3, type=int, help="Priority 1-5 (default: 3)")
def add(title, project, priority):
    """Add a new task"""
    if not title:
        click.echo("❌ Error: --title is required", err=True)
        sys.exit(2)
    try:
        task = manager.add_task(title=title, project=project, priority=priority)
        proj_str = f"Project: {task.project}, " if task.project else ""
        click.echo(f"✅ Added: [{task.id}] {task.title} ({proj_str}Priority: {task.priority})")
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
def list_tasks(status, project, priority, all_statuses):
    """List tasks"""
    try:
        tasks = manager.list_tasks(
            status=status,
            project=project,
            priority=priority,
            all_statuses=all_statuses,
        )
        if not tasks:
            click.echo("No tasks found.")
            return

        header = f"{'ID':<4} | {'Title':<22} | {'Project':<12} | {'Priority':<8} | {'Status':<12} | {'Created'}"
        separator = "-" * 4 + "-+-" + "-" * 22 + "-+-" + "-" * 12 + "-+-" + "-" * 8 + "-+-" + "-" * 12 + "-+-" + "-" * 10
        click.echo(header)
        click.echo(separator)
        for task in tasks:
            proj = task.project if task.project else "(none)"
            created = task.created_at.strftime("%Y-%m-%d")
            click.echo(
                f"{task.id:<4} | {task.title:<22} | {proj:<12} | {task.priority:<8} | {task.status:<12} | {created}"
            )
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
def update(task_id, title, project, clear_project, priority, status):
    """Update a task"""
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
@click.option("--id", "task_id", required=True, type=int, help="Task ID")
def remove(task_id):
    """Remove a task"""
    try:
        manager.remove_task(task_id)
        click.echo(f"✅ Removed: [{task_id}]")
    except ValueError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)
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
        click.echo(f"Task [{task.id}]:")
        click.echo(f"  Title:     {task.title}")
        click.echo(f"  Project:   {proj}")
        click.echo(f"  Priority:  {task.priority}")
        click.echo(f"  Status:    {task.status}")
        click.echo(f"  Created:   {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        click.echo(f"  Updated:   {task.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    except ValueError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
