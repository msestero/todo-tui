from __future__ import annotations

import shlex
from datetime import date
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Input, Label, ListView

import launcher
from forms import SubtaskForm, TodoForm
from parsing import next_occurrence
from row import Row
from store import DATA_PATH, Store
from subtask import Subtask
from todo_item import Todo
from todo_row import TodoRow


class TodoApp(App):
    CSS = """
    Screen { layout: vertical; }
    #title { padding: 0 1; color: $accent; text-style: bold; }
    #stats { padding: 0 1; color: $text-muted; }
    ListView { height: 1fr; border: round $primary; padding: 0 1; }
    #new { dock: bottom; display: none; }
    #new.visible { display: block; }
    """

    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("s", "add_sub", "+Subtask"),
        Binding("e", "edit", "Edit"),
        Binding("space", "toggle", "Toggle"),
        Binding("enter", "toggle", "Toggle", show=False),
        Binding("d", "delete", "Delete"),
        Binding("c", "claude", "Claude"),
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
        # Inline input is only used for the score: flow now.
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

        def done(result: dict | None) -> None:
            if result is None:
                return
            self.store.todos.append(Todo.new(
                result["text"],
                repeat=result["repeat"],
                max_score=result["max_score"],
                folder=result["folder"],
                depends_on=result["depends_on"],
            ))
            self.store.save()
            self.refresh_list()

        self.push_screen(
            TodoForm(title="New todo", candidates=self._dependency_candidates(None)),
            done,
        )

    def action_add_sub(self) -> None:
        if not self._viewing_today():
            self.notify("Switch to today (t) to add.", severity="warning")
            return
        row = self._selected_row()
        if row is None:
            self.notify("Select a parent todo first.", severity="warning")
            return
        parent = row.parent

        def done(text: str | None) -> None:
            if not text:
                return
            parent.subtasks.append(Subtask.new(text))
            self.store.save()
            self.refresh_list()

        self.push_screen(SubtaskForm(title=f"Subtask of: {parent.text}"), done)

    def action_edit(self) -> None:
        row = self._selected_row()
        if row is None:
            self.notify("Select a todo first.", severity="warning")
            return
        if row.sub is None:
            self._edit_parent(row.parent)
        else:
            self._edit_subtask(row.sub)

    def _edit_parent(self, t: Todo) -> None:
        initial = {
            "text": t.text,
            "max_score": t.max_score,
            "repeat": t.repeat,
            "folder": t.folder,
            "depends_on": t.depends_on,
        }

        def done(result: dict | None) -> None:
            if result is None:
                return
            t.text = result["text"]
            t.max_score = result["max_score"]
            if t.max_score is None:
                t.score = None
            t.repeat = result["repeat"]
            t.depends_on = result["depends_on"]
            new_folder = result["folder"]
            if new_folder != t.folder:
                t.folder = new_folder
                if new_folder is None:
                    t.claude_window = None
            self.store.save()
            self.refresh_list()

        self.push_screen(
            TodoForm(
                title=f"Edit: {t.text}",
                initial=initial,
                candidates=self._dependency_candidates(t.lineage_id),
            ),
            done,
        )

    def _dependency_candidates(self, exclude_lineage: str | None) -> list[tuple[str, str]]:
        """Distinct (label, lineage_id) pairs from todos in view, minus self."""
        seen: dict[str, str] = {}
        for t in self.store.by_date(self.current_date):
            if t.lineage_id == exclude_lineage:
                continue
            seen.setdefault(t.lineage_id, t.text)
        return [(text, lineage) for lineage, text in seen.items()]

    def _edit_subtask(self, s: Subtask) -> None:
        def done(text: str | None) -> None:
            if not text:
                return
            s.text = text
            self.store.save()
            self.refresh_list()

        self.push_screen(SubtaskForm(title="Edit subtask", initial_text=s.text), done)

    def action_claude(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        project = row.parent
        if not project.folder:
            self.notify("Attach a folder first (edit with e) to use Claude here.", severity="warning")
            return
        if not Path(project.folder).is_dir():
            self.notify(f"Folder no longer exists: {project.folder}", severity="error")
            return
        if row.sub is None:
            self._launch_main_session(project)
        else:
            self._launch_subtask_session(project, row.sub)

    def _launch_main_session(self, project: Todo) -> None:
        window = project.claude_window or f"todo-{project.id}"
        prompt = (
            f"This is the design session for the coding project {project.text!r}. "
            "You are running in the project's own folder. Work with me to: "
            "(1) plan the build as concrete, ordered steps; and "
            "(2) create and keep updating a CLAUDE.md in this folder that "
            "captures the architecture, conventions, and plan — later Claude "
            "sessions build the individual steps in this same folder and rely "
            "on that CLAUDE.md for guidance. "
            f"The todo-tui data file is {DATA_PATH}; this project is the todo "
            f'with id "{project.id}". As we agree on a step, append it to that '
            'todo\'s "subtasks" list as {"id": <8 hex chars>, "text": <step>, '
            '"done": false, "status": "proposed"}, so I can curate it in the TUI.'
        )
        try:
            launcher.open_session(
                project.folder, "claude " + shlex.quote(prompt),
                window_name=window, reuse=True,
            )
        except RuntimeError as e:
            self.notify(str(e), severity="error")
            return
        project.claude_window = window
        self.store.save()
        self.refresh_list()
        self.notify(f"Design session: {project.text}")

    def _launch_subtask_session(self, project: Todo, sub: Subtask) -> None:
        siblings = [s.text for s in project.subtasks if s.id != sub.id]
        context = f" Other planned steps: {'; '.join(siblings)}." if siblings else ""
        prompt = (
            f"You're implementing one step of the project {project.text!r}, in "
            f"the folder {project.folder}. The step to do: {sub.text}.{context}"
        )
        try:
            launcher.open_session(project.folder, "claude " + shlex.quote(prompt))
        except RuntimeError as e:
            self.notify(str(e), severity="error")
            return
        self.notify(f"Claude on: {sub.text}")

    @on(Input.Submitted, "#new")
    def add_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        mode = self._input_mode
        self._close_input()
        if not text or mode is None:
            return

        if mode.startswith("score:"):
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

    def _dependency_block(self, t: Todo) -> Todo | None:
        """If t depends on another todo for the same date, return it when it's not done."""
        if not t.depends_on:
            return None
        dep = next(
            (x for x in self.store.todos
             if x.date == t.date and x.lineage_id == t.depends_on),
            None,
        )
        if dep is not None and not dep.done:
            return dep
        return None

    def _complete_parent(self, t: Todo, score: int | None = None) -> None:
        """Mark parent done. Handles scoring and repeating-task spawn."""
        today = date.today().isoformat()
        t.done = True
        t.date = today
        if t.max_score is not None and score is not None:
            t.score = score
        if t.repeat:
            next_d = next_occurrence(t.repeat, date.today())
            clone = Todo.new(t.text, repeat=t.repeat, max_score=t.max_score, folder=t.folder)
            clone.date = next_d.isoformat()
            clone.subtasks = [Subtask.new(s.text) for s in t.subtasks]
            clone.lineage_id = t.lineage_id
            clone.depends_on = t.depends_on
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
                blocker = self._dependency_block(t)
                if blocker is not None:
                    self.notify(f"Finish '{blocker.text}' first.", severity="warning")
                    return
                if t.max_score is not None:
                    self._open_input(f"Score for '{t.text}' (0..{t.max_score})", f"score:{t.id}")
                    return
                self._complete_parent(t)
        else:
            s = row.sub
            parent = row.parent
            if not s.done:
                blocker = self._dependency_block(parent)
                if blocker is not None:
                    self.notify(f"Finish '{blocker.text}' first.", severity="warning")
                    return
            s.done = not s.done
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
