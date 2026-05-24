"""Tests for non-UI logic on TodoApp — completion helpers and parent/subtask sync.

We avoid instantiating TodoApp (which would pull in Textual's event loop) by
calling the methods directly with a minimal stub for `self`.
Flatten/collapse logic is tested separately in test_view_model.py.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app import TodoApp
from subtask import Subtask
from todo_item import Todo


def _toggle_stub():
    """Stub that exposes the completion helpers `_toggle_subtask` calls on self."""
    s = SimpleNamespace()
    s._complete_parent = lambda todo: TodoApp._complete_parent(s, todo)
    s._uncomplete_parent = lambda todo: TodoApp._uncomplete_parent(s, todo)
    return s


def _todo_with_subs(text: str, sub_texts: list[str]) -> Todo:
    t = Todo.new(text)
    t.subtasks = [Subtask.new(s) for s in sub_texts]
    return t


# ---------------- completion helpers ----------------


def test_complete_parent_sets_done_and_dates_today():
    t = Todo.new("x")
    t.date = "2020-01-01"
    TodoApp._complete_parent(SimpleNamespace(), t)
    assert t.done is True
    assert t.date == date.today().isoformat()


def test_uncomplete_parent_resets_done_and_dates_today():
    t = Todo.new("x")
    t.done = True
    t.date = "2020-01-01"
    TodoApp._uncomplete_parent(SimpleNamespace(), t)
    assert t.done is False
    assert t.date == date.today().isoformat()


# ---------------- subtask toggle / parent sync ----------------


def test_toggle_last_subtask_auto_completes_parent():
    t = _todo_with_subs("p", ["a", "b"])
    t.subtasks[0].done = True  # one of two done already
    TodoApp._toggle_subtask(_toggle_stub(), t, t.subtasks[1])
    assert t.subtasks[1].done is True
    assert t.done is True
    assert t.date == date.today().isoformat()


def test_unchecking_subtask_reopens_completed_parent():
    t = _todo_with_subs("p", ["a", "b"])
    for s in t.subtasks:
        s.done = True
    t.done = True
    TodoApp._toggle_subtask(_toggle_stub(), t, t.subtasks[0])
    assert t.subtasks[0].done is False
    assert t.done is False


def test_toggle_subtask_when_others_pending_does_not_complete_parent():
    t = _todo_with_subs("p", ["a", "b", "c"])
    TodoApp._toggle_subtask(_toggle_stub(), t, t.subtasks[0])
    assert t.subtasks[0].done is True
    assert t.done is False


def test_parent_with_no_subtasks_does_not_auto_complete():
    """all() on empty list is True, but a parent with no subs shouldn't
    become done via the subtask-toggle path. The code guards with
    `parent.subtasks and all(...)`."""
    t = Todo.new("p")
    phantom = Subtask.new("ghost")
    TodoApp._toggle_subtask(_toggle_stub(), t, phantom)
    assert t.done is False
