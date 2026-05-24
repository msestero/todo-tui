"""Tests for non-UI logic on TodoApp — flatten/collapse and completion helpers.

We avoid instantiating TodoApp (which would pull in Textual's event loop) by
calling the methods directly with a minimal stub for `self`.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app import TodoApp
from row import Row
from subtask import Subtask
from todo_item import Todo


def _stub(collapsed=None):
    return SimpleNamespace(_collapsed=collapsed or set())


def _toggle_stub():
    """Stub that exposes the completion helpers `_toggle_subtask` calls on self."""
    s = SimpleNamespace()
    s._complete_parent = lambda todo: TodoApp._complete_parent(s, todo)
    s._uncomplete_parent = lambda todo: TodoApp._uncomplete_parent(s, todo)
    return s


def _todo_with_subs(text, sub_texts):
    t = Todo.new(text)
    t.subtasks = [Subtask.new(s) for s in sub_texts]
    return t


# ---------------- _flatten ----------------

def test_flatten_no_subtasks_yields_only_parent():
    t = Todo.new("solo")
    rows = TodoApp._flatten(_stub(), [t])
    assert rows == [Row(parent=t, sub=None)]


def test_flatten_includes_subtasks_in_order():
    t = _todo_with_subs("p", ["a", "b"])
    rows = TodoApp._flatten(_stub(), [t])
    assert len(rows) == 3
    assert rows[0].sub is None and rows[0].parent is t
    assert rows[1].sub is t.subtasks[0]
    assert rows[2].sub is t.subtasks[1]


def test_flatten_collapsed_parent_hides_subtasks_and_marks_row():
    t = _todo_with_subs("p", ["a", "b"])
    rows = TodoApp._flatten(_stub(collapsed={t.id}), [t])
    assert len(rows) == 1
    assert rows[0].sub is None
    assert rows[0].collapsed is True


def test_flatten_collapsed_parent_with_no_subtasks_does_not_show_indicator():
    """A parent with no subtasks shouldn't render '(0 hidden)' even if in
    the collapsed set."""
    t = Todo.new("empty")
    rows = TodoApp._flatten(_stub(collapsed={t.id}), [t])
    assert rows[0].collapsed is False


def test_flatten_multiple_parents_mixed_collapse():
    a = _todo_with_subs("a", ["a1"])
    b = _todo_with_subs("b", ["b1", "b2"])
    rows = TodoApp._flatten(_stub(collapsed={b.id}), [a, b])
    texts = [r.parent.text + ("/" + r.sub.text if r.sub else "") for r in rows]
    assert texts == ["a", "a/a1", "b"]


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
    # Toggle the remaining subtask
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
    # Construct a phantom sub and toggle it — should not flip parent done.
    phantom = Subtask.new("ghost")
    TodoApp._toggle_subtask(_toggle_stub(), t, phantom)
    assert t.done is False
