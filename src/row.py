from __future__ import annotations

from dataclasses import dataclass

from subtask import Subtask
from todo_item import Todo


@dataclass
class Row:
    parent: Todo
    sub: Subtask | None
    collapsed: bool = False
    done_hidden: int = 0  # count of done subtasks hidden via the hide-done toggle
