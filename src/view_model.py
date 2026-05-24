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
    """Flatten parents and subtasks into the display list, honoring collapse.

    Done items sort toward the bottom — parents within the day, and subtasks
    within their parent. The sort is stable, so relative order within the
    done/pending groups is preserved."""
    rows: list[Row] = []
    for todo in sorted(todos, key=lambda t: t.done):
        rows.append(_parent_row(todo, state))
        if todo.id in state.collapsed:
            continue
        subs = sorted(todo.subtasks, key=lambda s: s.done)
        rows.extend(Row(parent=todo, sub=sub) for sub in subs)
    return rows


def _parent_row(todo: Todo, state: ViewState) -> Row:
    collapsed = todo.id in state.collapsed and bool(todo.subtasks)
    return Row(parent=todo, sub=None, collapsed=collapsed)
