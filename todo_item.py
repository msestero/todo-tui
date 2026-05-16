from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from subtask import Subtask


@dataclass
class Todo:
    id: str
    text: str
    date: str
    done: bool = False
    subtasks: list[Subtask] = field(default_factory=list)
    repeat: str | None = None  # "daily" | "weekdays" | "weekly" | "<N>d"
    max_score: int | None = None
    score: int | None = None

    @staticmethod
    def new(text: str, repeat: str | None = None, max_score: int | None = None) -> "Todo":
        return Todo(
            id=uuid.uuid4().hex[:8],
            text=text,
            date=date.today().isoformat(),
            repeat=repeat,
            max_score=max_score,
        )

    @classmethod
    def from_dict(cls, raw: dict) -> "Todo":
        return cls(
            id=raw["id"],
            text=raw["text"],
            date=raw["date"],
            done=raw.get("done", False),
            subtasks=[Subtask(**s) for s in raw.get("subtasks", [])],
            repeat=raw.get("repeat"),
            max_score=raw.get("max_score"),
            score=raw.get("score"),
        )
