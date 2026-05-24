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
    folders: list[str] = field(default_factory=list)
    claude_session_id: str | None = None

    @staticmethod
    def new(
        text: str,
        folders: list[str] | None = None,
        claude_session_id: str | None = None,
    ) -> Todo:
        return Todo(
            id=uuid.uuid4().hex[:8],
            text=text,
            date=date.today().isoformat(),
            folders=list(folders or []),
            claude_session_id=claude_session_id,
        )

    @classmethod
    def from_dict(cls, raw: dict) -> Todo:
        return cls(
            id=raw["id"],
            text=raw["text"],
            date=raw["date"],
            done=raw.get("done", False),
            subtasks=[Subtask.from_dict(s) for s in raw.get("subtasks", [])],
            folders=list(raw.get("folders") or []),
            claude_session_id=raw.get("claude_session_id"),
        )
