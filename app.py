from __future__ import annotations

from datetime import date

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Input, Label, ListView

from parsing import next_occurrence, parse_input
from row import Row
from store import Store
from subtask import Subtask
from todo_item import Todo
from todo_row import TodoRow


class TodoApp(App):
    CSS = """
    Screen { layout: vertical; }
    #title { padding: 0 1; color: $accent; text-style: bold; }
    #stats { padding: 0 1; color: $text-muted; }
    ListView { height: 1fr; border: round $primary; padding: 0 1; }
    Input { dock: bottom; display: none; }
    Input.visible { display: block; }
    """

    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("s", "add_sub", "+Subtask"),
        Binding("space", "toggle", "Toggle"),
        Binding("enter", "toggle", "Toggle", show=False),
        Binding("d", "delete", "Delete"),
        Binding("left,h", "prev_day", "← Day"),
        Binding("right,l", "next_day", "Day →"),
        Binding("t", "today", "Today"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.store = Store.load()
        self.store.rollover()
        self.store.save()
        self.current_date = date.today().isoformat()
        self._rows: list[Row] = []
        # input mode: "new" (parent), "sub:<parent_id>", "score:<parent_id>"
        self._input_mode: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label("", id="title")
        yield Label("", id="stats")
        yield ListView(id="list")
        yield Input(id="new")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_list()

    def _viewing_today(self) -> bool:
        return self.current_date == date.today().isoformat()

    def _flatten(self, todos: list[Todo]) -> list[Row]:
        rows: list[Row] = []
        for t in todos:
            rows.append(Row(parent=t, sub=None))
            for s in t.subtasks:
                rows.append(Row(parent=t, sub=s))
        return rows

    def refresh_list(self) -> None:
        lv = self.query_one("#list", ListView)
        idx = lv.index or 0
        lv.clear()
        self._rows = self._flatten(self.store.by_date(self.current_date))
        for r in self._rows:
            lv.append(TodoRow(r))
        if self._rows:
            lv.index = min(idx, len(self._rows) - 1)

        d = date.fromisoformat(self.current_date)
        suffix = "  [dim](today)[/]" if self._viewing_today() else ""
        self.query_one("#title", Label).update(f"{d.strftime('%A, %B %d, %Y')}{suffix}")

        parents = self.store.by_date(self.current_date)
        done = sum(1 for t in parents if t.done)
        total_score = sum(t.score for t in parents if t.score is not None)
        max_score = sum(t.max_score for t in parents if t.max_score is not None)
        score_chunk = f"   score {total_score}/{max_score}" if max_score else ""
        self.query_one("#stats", Label).update(
            f"{done}/{len(parents)} done{score_chunk}   {self._nav_hint()}"
        )

    def _nav_hint(self) -> str:
        dates = self.store.dates()
        i = dates.index(self.current_date)
        left = f"[dim]←[/] {dates[i-1]}" if i > 0 else "[dim]   start[/]"
        right = f"{dates[i+1]} [dim]→[/]" if i < len(dates) - 1 else "[dim]end   [/]"
        return f"{left}   {right}"

    def _open_input(self, placeholder: str, mode: str) -> None:
        self._input_mode = mode
        inp = self.query_one("#new", Input)
        inp.placeholder = placeholder
        inp.add_class("visible")
        inp.focus()

    def _close_input(self) -> None:
        inp = self.query_one("#new", Input)
        inp.value = ""
        inp.remove_class("visible")
        self._input_mode = None
        self.query_one("#list", ListView).focus()

    def action_add(self) -> None:
        if not self._viewing_today():
            self.notify("Switch to today (t) to add.", severity="warning")
            return
        self._open_input("New todo… (use /N for max score, *daily *weekly *weekdays *Nd to repeat)", "new")

    def action_add_sub(self) -> None:
        if not self._viewing_today():
            self.notify("Switch to today (t) to add.", severity="warning")
            return
        row = self._selected_row()
        if row is None:
            self.notify("Select a parent todo first.", severity="warning")
            return
        self._open_input(f"Subtask of: {row.parent.text}", f"sub:{row.parent.id}")

    @on(Input.Submitted, "#new")
    def add_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        mode = self._input_mode
        self._close_input()
        if not text or mode is None:
            return

        if mode == "new":
            clean, repeat, max_score = parse_input(text)
            if not clean:
                return
            self.store.todos.append(Todo.new(clean, repeat=repeat, max_score=max_score))
        elif mode.startswith("sub:"):
            pid = mode.split(":", 1)[1]
            for t in self.store.todos:
                if t.id == pid:
                    t.subtasks.append(Subtask.new(text))
                    break
        elif mode.startswith("score:"):
            pid = mode.split(":", 1)[1]
            target = next((t for t in self.store.todos if t.id == pid), None)
            if target is None:
                return
            try:
                val = int(text)
            except ValueError:
                self.notify("Score must be an integer.", severity="error")
                return
            if target.max_score is not None and not (0 <= val <= target.max_score):
                self.notify(f"Score must be 0..{target.max_score}.", severity="error")
                return
            self._complete_parent(target, score=val)
        self.store.save()
        self.refresh_list()

    def on_key(self, event) -> None:
        if event.key == "escape":
            inp = self.query_one("#new", Input)
            if inp.has_class("visible"):
                self._close_input()
                event.stop()

    def _selected_row(self) -> Row | None:
        lv = self.query_one("#list", ListView)
        if lv.index is None or not self._rows:
            return None
        return self._rows[lv.index]

    def _complete_parent(self, t: Todo, score: int | None = None) -> None:
        """Mark parent done. Handles scoring and repeating-task spawn."""
        today = date.today().isoformat()
        t.done = True
        t.date = today
        if t.max_score is not None and score is not None:
            t.score = score
        if t.repeat:
            next_d = next_occurrence(t.repeat, date.today())
            clone = Todo.new(t.text, repeat=t.repeat, max_score=t.max_score)
            clone.date = next_d.isoformat()
            clone.subtasks = [Subtask.new(s.text) for s in t.subtasks]
            self.store.todos.append(clone)

    def _uncomplete_parent(self, t: Todo) -> None:
        t.done = False
        t.score = None
        t.date = date.today().isoformat()

    def action_toggle(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        if row.sub is None:
            t = row.parent
            if t.done:
                was_remote = not self._viewing_today()
                self._uncomplete_parent(t)
                if was_remote:
                    self.notify(f"Revived to today: {t.text}")
                    self.current_date = date.today().isoformat()
            else:
                if t.max_score is not None:
                    self._open_input(f"Score for '{t.text}' (0..{t.max_score})", f"score:{t.id}")
                    return
                self._complete_parent(t)
        else:
            s = row.sub
            s.done = not s.done
            parent = row.parent
            all_done = parent.subtasks and all(x.done for x in parent.subtasks)
            if all_done and not parent.done and parent.max_score is None:
                self._complete_parent(parent)
            elif not all_done and parent.done:
                self._uncomplete_parent(parent)
        self.store.save()
        self.refresh_list()

    def action_delete(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        if row.sub is None:
            self.store.todos = [x for x in self.store.todos if x.id != row.parent.id]
        else:
            row.parent.subtasks = [s for s in row.parent.subtasks if s.id != row.sub.id]
        self.store.save()
        self.refresh_list()

    def action_prev_day(self) -> None:
        dates = self.store.dates()
        i = dates.index(self.current_date)
        if i > 0:
            self.current_date = dates[i - 1]
            self.refresh_list()

    def action_next_day(self) -> None:
        dates = self.store.dates()
        i = dates.index(self.current_date)
        if i < len(dates) - 1:
            self.current_date = dates[i + 1]
            self.refresh_list()

    def action_today(self) -> None:
        self.current_date = date.today().isoformat()
        self.refresh_list()
