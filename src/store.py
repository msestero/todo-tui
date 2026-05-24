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

    @classmethod
    def load(cls) -> "Store":
        if not DATA_PATH.exists():
            return cls()
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        return cls(todos=[Todo.from_dict(t) for t in raw.get("todos", [])])

    def save(self) -> None:
        """Atomic write: dump to a sibling temp file, then rename over the target."""
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = DATA_PATH.with_suffix(DATA_PATH.suffix + ".tmp")
        payload = json.dumps({"todos": [asdict(t) for t in self.todos]}, indent=2)
        tmp_path.write_text(payload, encoding="utf-8")
        os.replace(tmp_path, DATA_PATH)

    def rollover(self) -> int:
        """Move every unfinished past-dated todo to today. Returns the count moved."""
        today = date.today().isoformat()
        moved = 0
        for todo in self.todos:
            if not todo.done and todo.date < today:
                todo.date = today
                moved += 1
        return moved

    def dates(self) -> list[str]:
        # Future-dated todos (e.g. spawned by repeating tasks) exist in storage
        # but stay hidden from navigation until their day actually arrives.
        today = date.today().isoformat()
        visible = {todo.date for todo in self.todos if todo.date <= today}
        visible.add(today)
        return sorted(visible)

    def by_date(self, target_date: str) -> list[Todo]:
        return [todo for todo in self.todos if todo.date == target_date]
