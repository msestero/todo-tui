"""Pure view-model layer: turn a list of `Todo`s plus a `ViewState` into the
flat list of `Row`s the ListView renders.

No Textual imports here. Everything is testable without an app instance.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from row import Row
from todo_item import Todo


@dataclass
class ViewState:
    """Holds presentation state that's orthogonal to the stored data.

    - `collapsed`: parent ids whose subtasks are fully hidden (the existing
      enter-to-collapse behavior).
    - `hide_done`: parent ids whose *done* subtasks are hidden but pending
      subtasks still show. Independent from `collapsed`; if a parent is fully
      collapsed, that wins."""

    collapsed: set[str] = field(default_factory=set)
    hide_done: set[str] = field(default_factory=set)


def build_rows(todos: list[Todo], state: ViewState) -> list[Row]:
    """Flatten parents and subtasks into the display list, honoring collapse.

    Done items sort toward the bottom — parents within the day, and subtasks
    within their parent. The sort is stable, so relative order within the
    done/pending groups is preserved."""
    rows: list[Row] = []
    for todo in sorted(todos, key=lambda t: t.done):
        rows.append(_parent_row(todo, state))
        if todo.id in state.collapsed:
            continue
        visible_subs = _visible_subtasks(todo, state)
        rows.extend(Row(parent=todo, sub=sub) for sub in visible_subs)
    return rows


def _parent_row(todo: Todo, state: ViewState) -> Row:
    collapsed = todo.id in state.collapsed and bool(todo.subtasks)
    done_hidden = (
        sum(1 for s in todo.subtasks if s.done)
        if (todo.id in state.hide_done and not collapsed)
        else 0
    )
    return Row(parent=todo, sub=None, collapsed=collapsed, done_hidden=done_hidden)


def _visible_subtasks(todo: Todo, state: ViewState):
    subs = todo.subtasks
    if todo.id in state.hide_done:
        subs = [s for s in subs if not s.done]
    return sorted(subs, key=lambda s: s.done)
