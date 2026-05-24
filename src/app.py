from __future__ import annotations

import subprocess
import uuid
from dataclasses import asdict
from datetime import date
from pathlib import Path

from rich.table import Table
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label, ListView, Static

import launcher
from claude_context import build_context
from forms import ItemFormResult, NewFolderForm, SubtaskForm, TodoForm
from row import Row
from store import Store
from subtask import Subtask
from todo_item import Todo
from todo_row import TodoRow
from view_model import ViewState, build_rows
from week_row_widget import WeekRowWidget
from week_view import WeekRow, WeekViewState, build_week_rows, week_of

TODO_LIST_ROOT = Path.home() / "TodoList"


HELP_ENTRIES = [
    ("a", "Add a new todo (today only)"),
    ("s", "Add a subtask under the selected todo"),
    ("e", "Edit the selected todo or subtask"),
    ("c", "Open Claude session for the selected row (tmux)"),
    ("space", "Toggle done on the selected row"),
    ("enter", "Hide/show subtasks (list) or pick week/day (sidebar)"),
    ("d", "Delete the selected todo or subtask"),
    ("w", "Focus the week sidebar"),
    ("tab", "Cycle focus between sidebar and list"),
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
    #main { layout: horizontal; height: 1fr; }
    #sidebar { width: 22; border: round $primary; padding: 0 1; }
    #list { width: 1fr; border: round $primary; padding: 0 1; }
    """

    BINDINGS = [
        Binding("a", "add", "Add", show=False),
        Binding("s", "add_sub", "+Subtask", show=False),
        Binding("e", "edit", "Edit", show=False),
        Binding("space", "toggle", "Toggle", show=False),
        Binding("d", "delete", "Delete", show=False),
        Binding("c", "claude", "Claude", show=False),
        Binding("w", "focus_sidebar", "Weeks", show=False),
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
        self._week_rows: list[WeekRow] = []
        self._view_state = ViewState()
        self._week_state = WeekViewState(expanded_week=week_of(date.today()).key)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label("", id="title")
        yield Label("", id="stats")
        with Horizontal(id="main"):
            yield ListView(id="sidebar")
            yield ListView(id="list")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_list()
        self.query_one("#list", ListView).focus()

    # ------------------------------------------------------------------ helpers

    def _viewing_today(self) -> bool:
        return self.current_date == date.today().isoformat()

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
        self._rows = build_rows(parents, self._view_state)
        self._render_rows()
        self._render_sidebar()
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

    def _render_sidebar(self) -> None:
        self._week_rows = build_week_rows(self.store.dates(), self._week_state)
        sidebar = self.query_one("#sidebar", ListView)
        sidebar.clear()
        for row in self._week_rows:
            sidebar.append(WeekRowWidget(row))
        # Keep the highlight on the row matching the currently-viewed day if it's
        # visible (i.e. the week is open); otherwise highlight that day's week header.
        target = self._sidebar_index_for_current_date()
        if target is not None:
            sidebar.index = target

    def _sidebar_index_for_current_date(self) -> int | None:
        viewed = date.fromisoformat(self.current_date)
        viewed_week_key = week_of(viewed).key
        header_index: int | None = None
        for i, wr in enumerate(self._week_rows):
            if wr.day == viewed:
                return i
            if wr.day is None and wr.week.key == viewed_week_key:
                header_index = i
        return header_index

    def _render_title(self) -> None:
        viewed = date.fromisoformat(self.current_date)
        suffix = "  [dim](today)[/]" if self._viewing_today() else ""
        self.query_one("#title", Label).update(f"{viewed.strftime('%A, %B %d, %Y')}{suffix}")

    def _render_stats(self, parents: list[Todo]) -> None:
        done = sum(1 for todo in parents if todo.done)
        self.query_one("#stats", Label).update(f"{done}/{len(parents)} done")

    # ------------------------------------------------------------------ actions: add / edit

    def action_add(self) -> None:
        if not self._viewing_today():
            self.notify("Switch to today (t) to add.", severity="warning")
            return

        def on_save(result: ItemFormResult | None) -> None:
            if result is None:
                return
            self.store.todos.append(Todo.new(**asdict(result)))
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

        def on_save(result: ItemFormResult | None) -> None:
            if result is None:
                return
            parent.subtasks.append(Subtask.new(**asdict(result)))
            self._save_and_refresh()

        self.push_screen(SubtaskForm(initial=ItemFormResult()), on_save)

    def action_edit(self) -> None:
        row = self._selected_row()
        if row is None:
            self.notify("Select a todo first.", severity="warning")
            return
        target = row.sub or row.parent
        form_cls = SubtaskForm if row.sub else TodoForm
        initial = ItemFormResult(
            text=target.text,
            folders=list(target.folders),
            claude_session_id=target.claude_session_id,
        )

        def on_save(result: ItemFormResult | None) -> None:
            if result is None:
                return
            self._apply_form_result(target, result)
            self._save_and_refresh()

        self.push_screen(form_cls(initial=initial), on_save)

    @staticmethod
    def _apply_form_result(target: Todo | Subtask, result: ItemFormResult) -> None:
        target.text = result.text
        target.folders = result.folders
        target.claude_session_id = result.claude_session_id

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
        today = date.today().isoformat()
        if todo.done:
            was_remote = not self._viewing_today()
            todo.uncomplete(today)
            if was_remote:
                self.notify(f"Revived to today: {todo.text}")
                self.current_date = today
            return
        todo.complete(today)

    def _toggle_subtask(self, parent: Todo, subtask: Subtask) -> None:
        subtask.done = not subtask.done
        all_done = parent.subtasks and all(s.done for s in parent.subtasks)
        today = date.today().isoformat()
        if all_done and not parent.done:
            parent.complete(today)
        elif not all_done and parent.done:
            parent.uncomplete(today)

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

    def action_today(self) -> None:
        self.current_date = date.today().isoformat()
        self._week_state.expanded_week = week_of(date.today()).key
        self.refresh_list()

    def action_focus_sidebar(self) -> None:
        self.query_one("#sidebar", ListView).focus()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    @on(ListView.Selected)
    def _on_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "sidebar":
            self._on_sidebar_select()
        else:
            self.action_toggle_hide_subtasks()

    def _on_sidebar_select(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        if sidebar.index is None or not self._week_rows:
            return
        wr = self._week_rows[sidebar.index]
        if wr.day is None:
            # Toggle this week. Opening a different one auto-closes the previous.
            self._week_state.expanded_week = (
                None if self._week_state.expanded_week == wr.week.key else wr.week.key
            )
            self.refresh_list()
            return
        # Day selected — jump to it and focus the todo list.
        self.current_date = wr.day.isoformat()
        self.refresh_list()
        self.query_one("#list", ListView).focus()

    def action_toggle_hide_subtasks(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        collapsed = self._view_state.collapsed
        parent_id = row.parent.id
        if parent_id in collapsed:
            collapsed.discard(parent_id)
        else:
            collapsed.add(parent_id)
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
                initial_context=build_context(parent),
            )
        except (RuntimeError, subprocess.CalledProcessError) as e:
            self.notify(f"Launch failed: {e}", severity="error")
            return
        self.notify(f"Claude on: {owner.text}")
