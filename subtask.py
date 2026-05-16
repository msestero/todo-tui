from __future__ import annotations

import uuid
from dataclasses import dataclass


# status values: "active" (a normal step), "proposed" (suggested by a Claude
# design session, awaiting curation), "skipped" (kept for the record, won't do).
@dataclass
class Subtask:
    id: str
    text: str
    done: bool = False
    status: str = "active"

    @staticmethod
    def new(text: str, status: str = "active") -> "Subtask":
        return Subtask(id=uuid.uuid4().hex[:8], text=text, status=status)

    @classmethod
    def from_dict(cls, raw: dict) -> "Subtask":
        return cls(
            id=raw["id"],
            text=raw["text"],
            done=raw.get("done", False),
            status=raw.get("status", "active"),
        )
