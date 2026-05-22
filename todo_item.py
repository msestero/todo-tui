from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from parsing import migrate_repeat
from subtask import Subtask


@dataclass
class Todo:
    id: str
    text: str
    date: str
    done: bool = False
    subtasks: list[Subtask] = field(default_factory=list)
    # See parsing.py for the structured repeat schema.
    repeat: dict | None = None
    max_score: int | None = None
    score: int | None = None
    folder: str | None = None  # absolute path; non-null marks a coding project
    claude_window: str | None = None  # tmux window name of its main design session
    lineage_id: str = ""  # stable across daily clones; falls back to id for legacy data
    depends_on: str | None = None  # lineage_id of prerequisite todo (habit hook)

    @staticmethod
    def new(
        text: str,
        repeat: dict | None = None,
        max_score: int | None = None,
        folder: str | None = None,
        depends_on: str | None = None,
    ) -> "Todo":
        new_id = uuid.uuid4().hex[:8]
        return Todo(
            id=new_id,
            text=text,
            date=date.today().isoformat(),
            repeat=repeat,
            max_score=max_score,
            folder=folder,
            lineage_id=new_id,
            depends_on=depends_on,
        )

    @classmethod
    def from_dict(cls, raw: dict) -> "Todo":
        return cls(
            id=raw["id"],
            text=raw["text"],
            date=raw["date"],
            done=raw.get("done", False),
            subtasks=[Subtask.from_dict(s) for s in raw.get("subtasks", [])],
            repeat=migrate_repeat(raw.get("repeat"), raw.get("date")),
            max_score=raw.get("max_score"),
            score=raw.get("score"),
            folder=raw.get("folder"),
            claude_window=raw.get("claude_window"),
            lineage_id=raw.get("lineage_id") or raw["id"],
            depends_on=raw.get("depends_on"),
        )
