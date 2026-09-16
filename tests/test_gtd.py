import json
from datetime import date, datetime, timedelta

import pytest
from click.testing import CliRunner

from gtd_cli.commands import TaskManager
from gtd_cli.main import cli
from gtd_cli.storage import TaskStorage
from gtd_cli.task import Task, normalize_context


@pytest.fixture
def task_file(tmp_path, monkeypatch):
    path = tmp_path / "tasks.json"
    monkeypatch.setenv("GTD_FILE", str(path))
    return path


@pytest.fixture
def run(task_file):
    runner = CliRunner()

    def _run(*args, input=None):
        return runner.invoke(cli, list(args), input=input, catch_exceptions=False)
    return _run


# ------------------------------------------------------------------ model
def test_context_normalization():
    assert normalize_context("office") == "@office"
    assert normalize_context("@Home") == "@home"
    assert normalize_context("  ") is None
    with pytest.raises(ValueError):
        normalize_context("@no spaces")


def test_task_validation():
    with pytest.raises(ValueError):
        Task(id=1, title="  ")
    with pytest.raises(ValueError):
        Task(id=1, title="x", priority=9)
    with pytest.raises(ValueError):
        Task(id=1, title="x", status="someday")


def test_v1_and_v2_files_still_load(task_file):
    """Files written by v1 (no due_date) and v2 (no context) load unchanged."""
    task_file.write_text(json.dumps({
        "tasks": [
            {"id": 1, "title": "v1 task", "project": None, "priority": 3, "status": "inbox",
             "created_at": "2026-03-01T10:00:00", "updated_at": "2026-03-01T10:00:00"},
            {"id": 2, "title": "v2 task", "project": "p", "priority": 5, "status": "next-action",
             "created_at": "2026-03-02T10:00:00", "updated_at": "2026-03-02T10:00:00",
             "due_date": "2026-03-10"},
        ],
        "next_id": 3,
    }), encoding="utf-8")
    tasks = TaskStorage().load_tasks()
    assert [t.due_date for t in tasks] == [None, date(2026, 3, 10)]
    assert [t.context for t in tasks] == [None, None]


# ------------------------------------------------------------------ storage
def test_backup_and_restore(task_file):
    storage = TaskStorage()
    manager = TaskManager(storage)
    manager.add_task("keep me")
    manager.remove_task(1)
    assert manager.storage.load_tasks() == []
    assert storage.restore_backup()
    assert [t.title for t in storage.load_tasks()] == ["keep me"]


def test_ids_are_never_reused(task_file):
    manager = TaskManager(TaskStorage())
    manager.add_task("a")
    manager.add_task("b")
    manager.remove_task(2)
    assert manager.add_task("c").id == 3


# ------------------------------------------------------------------ CLI
def test_add_list_check_flow(run):
    r = run("add", "--title", "Write report", "--project", "thesis", "--priority", "4",
            "--due", "2030-01-01", "--context", "office")
    assert r.exit_code == 0 and "[1] Write report" in r.output and "@office" in r.output

    r = run("list")
    assert "Write report" in r.output and "@office" in r.output

    r = run("check", "--id", "1")
    assert "Completed" in r.output
    assert "Write report" not in run("list").output          # done tasks hidden by default
    assert "Write report" in run("list", "--all").output


def test_add_requires_title(run):
    r = run("add")
    assert r.exit_code == 2 and "--title is required" in r.output


def test_invalid_date_is_exit_2(run):
    r = run("add", "--title", "x", "--due", "not-a-date")
    assert r.exit_code == 2 and "YYYY-MM-DD" in r.output


def test_next_filters_by_context(run):
    run("add", "--title", "Call plumber", "--context", "@phone")
    run("add", "--title", "Fix shelf", "--context", "@home")
    run("update", "--id", "1", "--status", "next-action")
    run("update", "--id", "2", "--status", "next-action")
    out = run("next", "--context", "@home").output
    assert "Fix shelf" in out and "Call plumber" not in out
    assert "No next actions in @office" in run("next", "--context", "@office").output


def test_list_sorts_overdue_first(run):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    run("add", "--title", "High prio", "--priority", "5")
    run("add", "--title", "Overdue low prio", "--priority", "1", "--due", yesterday)
    lines = [l for l in run("list").output.splitlines() if "|" in l][1:]
    assert "Overdue low prio" in lines[0] and "⚠️" in lines[0]


def test_update_mutually_exclusive_flags(run):
    run("add", "--title", "x")
    assert run("update", "--id", "1", "--due", "2030-01-01", "--no-due").exit_code == 2
    assert run("update", "--id", "1", "--context", "@a", "--no-context").exit_code == 2


def test_remove_confirmation_and_undo(run):
    run("add", "--title", "keep")
    run("add", "--title", "drop")
    r = run("remove", "--id", "2", input="n\n")
    assert "Cancelled" in r.output and "drop" in run("list").output

    r = run("remove", "--id", "2", "--id", "99", "--force")
    assert "Removed: [2]" in r.output and "Skipped: [99]" in r.output
    assert "drop" not in run("list").output

    assert run("undo").exit_code == 0
    assert "drop" in run("list").output


def test_review_sections(run, task_file):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    soon = (date.today() + timedelta(days=3)).isoformat()
    run("add", "--title", "late", "--due", yesterday)
    run("add", "--title", "soon", "--due", soon)
    run("add", "--title", "blocked")
    run("update", "--id", "3", "--status", "waiting")
    run("add", "--title", "finished")
    run("check", "--id", "4")
    # make task 2 stale by back-dating its updated_at
    data = json.loads(task_file.read_text(encoding="utf-8"))
    data["tasks"][1]["updated_at"] = (datetime.now() - timedelta(days=30)).isoformat()
    task_file.write_text(json.dumps(data), encoding="utf-8")

    out = run("review").output
    assert "Overdue (1)" in out and "[1] late" in out
    assert "Due in the next 7 days (1)" in out and "[2] soon" in out
    assert "Waiting for (1)" in out and "[3] blocked" in out
    assert "Stale" in out and "[2] soon" in out
    assert "Completed in the last 7 days (1)" in out and "[4] finished" in out


def test_report_counts(run):
    run("add", "--title", "a", "--project", "p")
    run("add", "--title", "b", "--project", "p")
    run("check", "--id", "2")
    out = run("report", "--project", "p").output
    assert "inbox:       1 tasks" in out and "done:        1 tasks" in out and "Total:       2 tasks" in out


def test_file_option_overrides_env(run, tmp_path):
    other = tmp_path / "other.json"
    run("--file", str(other), "add", "--title", "elsewhere")
    assert "elsewhere" in run("--file", str(other), "list").output
    assert "elsewhere" not in run("list").output
