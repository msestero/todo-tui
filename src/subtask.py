from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Subtask:
    id: str
    text: str
    done: bool = False
    folders: list[str] = field(default_factory=list)
    claude_session_id: str | None = None

    @staticmethod
    def new(
        text: str,
        folders: list[str] | None = None,
        claude_session_id: str | None = None,
    ) -> Subtask:
        return Subtask(
            id=uuid.uuid4().hex[:8],
            text=text,
            folders=list(folders or []),
            claude_session_id=claude_session_id,
        )

    @classmethod
    def from_dict(cls, raw: dict) -> Subtask:
        return cls(
            id=raw["id"],
            text=raw["text"],
            done=raw.get("done", False),
            folders=list(raw.get("folders") or []),
            claude_session_id=raw.get("claude_session_id"),
        )
