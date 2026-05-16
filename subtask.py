from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass
class Subtask:
    id: str
    text: str
    done: bool = False

    @staticmethod
    def new(text: str) -> "Subtask":
        return Subtask(id=uuid.uuid4().hex[:8], text=text)
