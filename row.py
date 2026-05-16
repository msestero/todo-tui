from __future__ import annotations

from dataclasses import dataclass

from subtask import Subtask
from todo_item import Todo


@dataclass
class Row:
    parent: Todo
    sub: Subtask | None
