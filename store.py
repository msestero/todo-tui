from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import date
from pathlib import Path

from todo_item import Todo


DATA_PATH = Path(os.environ.get("TODO_TUI_DATA", Path.home() / ".config" / "todo-tui" / "todos.json"))


@dataclass
class Store:
    todos: list[Todo] = field(default_factory=list)
    last_opened: str = ""

    @classmethod
    def load(cls) -> "Store":
        if not DATA_PATH.exists():
            return cls()
        raw = json.loads(DATA_PATH.read_text())
        return cls(
            todos=[Todo.from_dict(t) for t in raw.get("todos", [])],
            last_opened=raw.get("last_opened", ""),
        )

    def save(self) -> None:
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        DATA_PATH.write_text(
            json.dumps(
                {"todos": [asdict(t) for t in self.todos], "last_opened": self.last_opened},
                indent=2,
            )
        )

    def rollover(self) -> int:
        today = date.today().isoformat()
        moved = 0
        for t in self.todos:
            if not t.done and t.date < today:
                t.date = today
                moved += 1
        self.last_opened = today
        return moved

    def dates(self) -> list[str]:
        ds = {t.date for t in self.todos}
        ds.add(date.today().isoformat())
        return sorted(ds)

    def by_date(self, d: str) -> list[Todo]:
        return [t for t in self.todos if t.date == d]
