"""Tests for non-UI logic on TodoApp — parent/subtask sync.

We avoid instantiating TodoApp (which would pull in Textual's event loop) by
calling the methods directly with a plain `SimpleNamespace()` as `self`; the
methods no longer reach onto `self` for completion helpers (those now live on
`Todo` — see test_todo_item.py).
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app import TodoApp
from subtask import Subtask
from todo_item import Todo


def _todo_with_subs(text: str, sub_texts: list[str]) -> Todo:
    t = Todo.new(text)
    t.subtasks = [Subtask.new(s) for s in sub_texts]
    return t


def test_toggle_last_subtask_auto_completes_parent():
    t = _todo_with_subs("p", ["a", "b"])
    t.subtasks[0].done = True
    TodoApp._toggle_subtask(SimpleNamespace(), t, t.subtasks[1])
    assert t.subtasks[1].done is True
    assert t.done is True
    assert t.date == date.today().isoformat()


def test_unchecking_subtask_reopens_completed_parent():
    t = _todo_with_subs("p", ["a", "b"])
    for s in t.subtasks:
        s.done = True
    t.done = True
    TodoApp._toggle_subtask(SimpleNamespace(), t, t.subtasks[0])
    assert t.subtasks[0].done is False
    assert t.done is False


def test_toggle_subtask_when_others_pending_does_not_complete_parent():
    t = _todo_with_subs("p", ["a", "b", "c"])
    TodoApp._toggle_subtask(SimpleNamespace(), t, t.subtasks[0])
    assert t.subtasks[0].done is True
    assert t.done is False


def test_parent_with_no_subtasks_does_not_auto_complete():
    """all() on empty list is True, but a parent with no subs shouldn't
    become done via the subtask-toggle path. The code guards with
    `parent.subtasks and all(...)`."""
    t = Todo.new("p")
    phantom = Subtask.new("ghost")
    TodoApp._toggle_subtask(SimpleNamespace(), t, phantom)
    assert t.done is False
