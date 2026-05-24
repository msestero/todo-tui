from __future__ import annotations

import subprocess
import uuid
from datetime import date
from pathlib import Path

from rich.table import Table

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label, ListView, Static

import launcher
from forms import NewFolderForm, SubtaskForm, TodoForm
from row import Row
from store import Store
from subtask import Subtask
from todo_item import Todo
from todo_row import TodoRow


TODO_LIST_ROOT = Path.home() / "TodoList"


HELP_ENTRIES = [
    ("a", "Add a new todo (today only)"),
    ("s", "Add a subtask under the selected todo"),
    ("e", "Edit the selected todo or subtask"),
    ("c", "Open Claude session for the selected row (tmux)"),
    ("space", "Toggle done on the selected row"),
    ("enter", "Hide/show subtasks"),
    ("d", "Delete the selected todo or subtask"),
    ("← / h", "Previous day"),
    ("→ / l", "Next day"),
    ("t", "Jump to today"),
    ("?", "Show this help"),
    ("q", "Quit"),
]


class HelpScreen(ModalScreen[None]):
    CSS = """
    HelpScreen { align: center middle; }
    #card {
        width: 56; height: auto; padding: 1 2;
        background: $panel; border: round $primary;
    }
    #card .title { color: $accent; text-style: bold; padding-bottom: 1; }
    #card .hint { color: $text-muted; padding-top: 1; }
    """

    BINDINGS = [("escape,question_mark,q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        table = Table.grid(padding=(0, 2))
        table.add_column(no_wrap=True, style="bold")
        table.add_column(overflow="fold")
        for key, description in HELP_ENTRIES:
            table.add_row(key, description)
        with Vertical(id="card"):
            yield Static("Keys", classes="title")
            yield Static(table)
            yield Static("esc / ? / q to close", classes="hint")

    def action_dismiss(self) -> None:
        self.dismiss(None)


class TodoApp(App):
    CSS = """
    Screen { layout: vertical; }
    #title { padding: 0 1; color: $accent; text-style: bold; }
    #stats { padding: 0 1; color: $text-muted; }
    ListView { height: 1fr; border: round $primary; padding: 0 1; }
    """

    BINDINGS = [
        Binding("a", "add", "Add", show=False),
        Binding("s", "add_sub", "+Subtask", show=False),
        Binding("e", "edit", "Edit", show=False),
        Binding("space", "toggle", "Toggle", show=False),
        Binding("d", "delete", "Delete", show=False),
        Binding("c", "claude", "Claude", show=False),
        Binding("left,h", "prev_day", "← Day", show=False),
        Binding("right,l", "next_day", "Day →", show=False),
        Binding("t", "today", "Today", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("question_mark", "help", "? Help"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.store = Store.load()
        self.store.rollover()
        self.store.save()
        self.current_date = date.today().isoformat()
        self._rows: list[Row] = []
        self._collapsed: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label("", id="title")
        yield Label("", id="stats")
        yield ListView(id="list")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_list()

    # ------------------------------------------------------------------ helpers

    def _viewing_today(self) -> bool:
        return self.current_date == date.today().isoformat()

    def _flatten(self, todos: list[Todo]) -> list[Row]:
        rows: list[Row] = []
        for todo in todos:
            is_collapsed = todo.id in self._collapsed and bool(todo.subtasks)
            rows.append(Row(parent=todo, sub=None, collapsed=is_collapsed))
            if todo.id in self._collapsed:
                continue
            for subtask in todo.subtasks:
                rows.append(Row(parent=todo, sub=subtask))
        return rows

    def _selected_row(self) -> Row | None:
        list_view = self.query_one("#list", ListView)
        if list_view.index is None or not self._rows:
            return None
        return self._rows[list_view.index]

    def _save_and_refresh(self) -> None:
        self.store.save()
        self.refresh_list()

    # ------------------------------------------------------------------ view

    def refresh_list(self) -> None:
        parents = self.store.by_date(self.current_date)
        self._rows = self._flatten(parents)
        self._render_rows()
        self._render_title()
        self._render_stats(parents)

    def _render_rows(self) -> None:
        list_view = self.query_one("#list", ListView)
        previous_index = list_view.index or 0
        list_view.clear()
        for row in self._rows:
            list_view.append(TodoRow(row))
        if self._rows:
            list_view.index = min(previous_index, len(self._rows) - 1)

    def _render_title(self) -> None:
        viewed = date.fromisoformat(self.current_date)
        suffix = "  [dim](today)[/]" if self._viewing_today() else ""
        self.query_one("#title", Label).update(
            f"{viewed.strftime('%A, %B %d, %Y')}{suffix}"
        )

    def _render_stats(self, parents: list[Todo]) -> None:
        done = sum(1 for todo in parents if todo.done)
        self.query_one("#stats", Label).update(
            f"{done}/{len(parents)} done   {self._nav_hint()}"
        )

    def _nav_hint(self) -> str:
        dates = self.store.dates()
        i = dates.index(self.current_date)
        left = f"[dim]←[/] {dates[i-1]}" if i > 0 else "[dim]   start[/]"
        right = f"{dates[i+1]} [dim]→[/]" if i < len(dates) - 1 else "[dim]end   [/]"
        return f"{left}   {right}"

    # ------------------------------------------------------------------ completion

    def _complete_parent(self, todo: Todo) -> None:
        todo.done = True
        todo.date = date.today().isoformat()

    def _uncomplete_parent(self, todo: Todo) -> None:
        todo.done = False
        todo.date = date.today().isoformat()

    # ------------------------------------------------------------------ actions: add / edit

    def action_add(self) -> None:
        if not self._viewing_today():
            self.notify("Switch to today (t) to add.", severity="warning")
            return

        def on_save(result: dict | None) -> None:
            if result is None:
                return
            self.store.todos.append(Todo.new(
                result["text"],
                folders=result["folders"],
                claude_session_id=result["claude_session_id"],
            ))
            self._save_and_refresh()

        self.push_screen(TodoForm(), on_save)

    def action_add_sub(self) -> None:
        if not self._viewing_today():
            self.notify("Switch to today (t) to add.", severity="warning")
            return
        row = self._selected_row()
        if row is None:
            self.notify("Select a parent todo first.", severity="warning")
            return
        parent = row.parent

        def on_save(result: dict | None) -> None:
            if result is None:
                return
            parent.subtasks.append(Subtask.new(
                result["text"],
                folders=result["folders"],
                claude_session_id=result["claude_session_id"],
            ))
            self._save_and_refresh()

        self.push_screen(SubtaskForm(), on_save)

    def action_edit(self) -> None:
        row = self._selected_row()
        if row is None:
            self.notify("Select a todo first.", severity="warning")
            return
        if row.sub is None:
            self._edit_parent(row.parent)
        else:
            self._edit_subtask(row.sub)

    def _edit_parent(self, todo: Todo) -> None:
        initial = {
            "text": todo.text,
            "folders": todo.folders,
            "claude_session_id": todo.claude_session_id,
        }

        def on_save(result: dict | None) -> None:
            if result is None:
                return
            todo.text = result["text"]
            todo.folders = result["folders"]
            todo.claude_session_id = result["claude_session_id"]
            self._save_and_refresh()

        self.push_screen(TodoForm(initial=initial), on_save)

    def _edit_subtask(self, subtask: Subtask) -> None:
        initial = {
            "text": subtask.text,
            "folders": subtask.folders,
            "claude_session_id": subtask.claude_session_id,
        }

        def on_save(result: dict | None) -> None:
            if result is None:
                return
            subtask.text = result["text"]
            subtask.folders = result["folders"]
            subtask.claude_session_id = result["claude_session_id"]
            self._save_and_refresh()

        self.push_screen(SubtaskForm(initial=initial), on_save)

    # ------------------------------------------------------------------ actions: toggle / delete

    def action_toggle(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        if row.sub is None:
            self._toggle_parent(row.parent)
        else:
            self._toggle_subtask(row.parent, row.sub)
        self._save_and_refresh()

    def _toggle_parent(self, todo: Todo) -> None:
        if todo.done:
            was_remote = not self._viewing_today()
            self._uncomplete_parent(todo)
            if was_remote:
                self.notify(f"Revived to today: {todo.text}")
                self.current_date = date.today().isoformat()
            return
        self._complete_parent(todo)

    def _toggle_subtask(self, parent: Todo, subtask: Subtask) -> None:
        subtask.done = not subtask.done
        all_done = parent.subtasks and all(s.done for s in parent.subtasks)
        if all_done and not parent.done:
            self._complete_parent(parent)
        elif not all_done and parent.done:
            self._uncomplete_parent(parent)

    def action_delete(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        if row.sub is None:
            self.store.todos = [t for t in self.store.todos if t.id != row.parent.id]
        else:
            row.parent.subtasks = [s for s in row.parent.subtasks if s.id != row.sub.id]
        self._save_and_refresh()

    # ------------------------------------------------------------------ actions: navigation / help

    def _step_day(self, delta: int) -> None:
        dates = self.store.dates()
        i = dates.index(self.current_date) + delta
        if 0 <= i < len(dates):
            self.current_date = dates[i]
            self.refresh_list()

    def action_prev_day(self) -> None:
        self._step_day(-1)

    def action_next_day(self) -> None:
        self._step_day(1)

    def action_today(self) -> None:
        self.current_date = date.today().isoformat()
        self.refresh_list()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    @on(ListView.Selected)
    def _on_selected(self, event: ListView.Selected) -> None:
        self.action_toggle_hide_subtasks()

    def action_toggle_hide_subtasks(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        parent_id = row.parent.id
        if parent_id in self._collapsed:
            self._collapsed.discard(parent_id)
        else:
            self._collapsed.add(parent_id)
        self.refresh_list()

    # ------------------------------------------------------------------ actions: claude

    def action_claude(self) -> None:
        row = self._selected_row()
        if row is None:
            self.notify("Select a row first.", severity="warning")
            return

        parent = row.parent
        subtask = row.sub
        # Subtasks inherit folders from the parent; the session is always their own.
        folders_owner = subtask if (subtask and subtask.folders) else parent
        existing_folders = list(folders_owner.folders)
        session_id = subtask.claude_session_id if subtask else parent.claude_session_id

        if existing_folders:
            self._launch_claude(existing_folders, session_id, parent, subtask)
            return

        # No folder anywhere up the chain — prompt to create one under ~/TodoList/.
        def on_name(name: str | None) -> None:
            if not name:
                return
            try:
                new_path = self._create_todo_folder(name)
            except OSError as e:
                self.notify(f"Could not create folder: {e}", severity="error")
                return
            # Always attach the newly-created folder to the parent (subtasks inherit).
            parent.folders.append(str(new_path))
            self._save_and_refresh()
            self._launch_claude(parent.folders, session_id, parent, subtask)

        self.push_screen(NewFolderForm(), on_name)

    @staticmethod
    def _create_todo_folder(name: str) -> Path:
        TODO_LIST_ROOT.mkdir(parents=True, exist_ok=True)
        path = TODO_LIST_ROOT / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _launch_claude(
        self,
        folders: list[str],
        session_id: str | None,
        parent: Todo,
        subtask: Subtask | None,
    ) -> None:
        resolved: list[str] = []
        for folder in folders:
            path = Path(folder).expanduser()
            if not path.is_dir():
                self.notify(f"Folder does not exist: {path}", severity="error")
                return
            resolved.append(str(path))

        owner = subtask or parent

        # If this row doesn't yet have a session id, mint one and bind it to
        # claude via --session-id. That way the id is known up front, no polling.
        resume = session_id is not None
        if session_id is None:
            session_id = str(uuid.uuid4())
            owner.claude_session_id = session_id
            self._save_and_refresh()

        try:
            launcher.launch(
                resolved,
                session_id,
                resume=resume,
                window_name=owner.text,
                session_name=f"todo-{owner.id}",
            )
        except (RuntimeError, subprocess.CalledProcessError) as e:
            self.notify(f"Launch failed: {e}", severity="error")
            return
        self.notify(f"Claude on: {owner.text}")
