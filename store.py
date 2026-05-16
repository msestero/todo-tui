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
    # mtime of DATA_PATH when last read; used to detect external writes.
    _loaded_mtime: float | None = field(default=None, repr=False)

    @classmethod
    def load(cls) -> "Store":
        if not DATA_PATH.exists():
            return cls()
        raw = json.loads(DATA_PATH.read_text())
        store = cls(
            todos=[Todo.from_dict(t) for t in raw.get("todos", [])],
            last_opened=raw.get("last_opened", ""),
        )
        store._loaded_mtime = DATA_PATH.stat().st_mtime
        return store

    def _merge_external(self) -> None:
        """The file changed under us (e.g. a Claude design session wrote to it).
        Pull in todos and subtasks we don't have so external additions survive
        our save. Our in-memory state wins for anything we already track."""
        try:
            raw = json.loads(DATA_PATH.read_text())
        except (OSError, ValueError):
            return
        by_id = {t.id: t for t in self.todos}
        for dt in (Todo.from_dict(t) for t in raw.get("todos", [])):
            mine = by_id.get(dt.id)
            if mine is None:
                self.todos.append(dt)
                continue
            have = {s.id for s in mine.subtasks}
            mine.subtasks.extend(s for s in dt.subtasks if s.id not in have)

    def save(self) -> None:
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        if self._loaded_mtime is not None and DATA_PATH.exists():
            if DATA_PATH.stat().st_mtime > self._loaded_mtime:
                self._merge_external()
        DATA_PATH.write_text(
            json.dumps(
                {"todos": [asdict(t) for t in self.todos], "last_opened": self.last_opened},
                indent=2,
            )
        )
        self._loaded_mtime = DATA_PATH.stat().st_mtime

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
        # Future-dated todos (e.g. spawned by repeating tasks) exist in storage
        # but stay hidden from navigation until their day actually arrives.
        today = date.today().isoformat()
        ds = {t.date for t in self.todos if t.date <= today}
        ds.add(today)
        return sorted(ds)

    def by_date(self, d: str) -> list[Todo]:
        return [t for t in self.todos if t.date == d]
