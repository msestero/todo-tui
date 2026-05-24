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

    Currently just `collapsed` parent ids. Future axes (e.g. hiding done
    subtasks, sort order) belong here too — they're all per-session display
    state, not data."""

    collapsed: set[str] = field(default_factory=set)


def build_rows(todos: list[Todo], state: ViewState) -> list[Row]:
    """Flatten parents and subtasks into the display list, honoring collapse."""
    rows: list[Row] = []
    for todo in todos:
        rows.append(_parent_row(todo, state))
        if todo.id in state.collapsed:
            continue
        rows.extend(Row(parent=todo, sub=sub) for sub in todo.subtasks)
    return rows


def _parent_row(todo: Todo, state: ViewState) -> Row:
    collapsed = todo.id in state.collapsed and bool(todo.subtasks)
    return Row(parent=todo, sub=None, collapsed=collapsed)
