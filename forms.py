from __future__ import annotations

from datetime import date
from pathlib import Path

from rich.text import Text

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Select


DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class DaysSelector(Widget, can_focus=True):
    """Single focusable widget. Left/Right move cursor, Enter/Space toggles."""

    DEFAULT_CSS = """
    DaysSelector {
        height: 3;
        width: auto;
        padding: 0;
    }
    DaysSelector:focus {
        /* cursor styling is in the render itself */
    }
    """

    BINDINGS = [
        ("left", "move(-1)", "Prev day"),
        ("right", "move(1)", "Next day"),
        ("home", "move_to(0)", "First"),
        ("end", "move_to(6)", "Last"),
        ("space,enter", "toggle", "Toggle"),
    ]

    cursor: reactive[int] = reactive(0)

    def __init__(self, selected: set[int] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.selected: set[int] = set(selected or ())

    def render(self) -> Text:
        focused = self.has_focus
        text = Text()
        for i, label in enumerate(DAY_LABELS):
            is_sel = i in self.selected
            is_cur = i == self.cursor and focused
            if is_sel and is_cur:
                style = "bold black on bright_yellow"
            elif is_sel:
                style = "bold black on cyan"
            elif is_cur:
                style = "reverse"
            else:
                style = "dim"
            text.append(f" {label} ", style=style)
            if i != len(DAY_LABELS) - 1:
                text.append(" ")
        return text

    def watch_cursor(self) -> None:
        self.refresh()

    def on_focus(self) -> None:
        self.refresh()

    def on_blur(self) -> None:
        self.refresh()

    def action_move(self, delta: int) -> None:
        self.cursor = (self.cursor + delta) % 7

    def action_move_to(self, idx: int) -> None:
        self.cursor = idx

    def action_toggle(self) -> None:
        if self.cursor in self.selected:
            self.selected.discard(self.cursor)
        else:
            self.selected.add(self.cursor)
        self.refresh()

    def on_click(self) -> None:
        self.focus()


class TodoForm(ModalScreen[dict | None]):
    """Add or edit a parent todo. Dismisses with a result dict or None."""

    CSS = """
    TodoForm { align: center middle; }
    #card {
        width: 64; height: auto; padding: 1 2;
        background: $panel; border: round $primary;
    }
    #card Label.title { color: $accent; text-style: bold; padding-bottom: 1; }
    #card Label.field { color: $text-muted; padding-top: 1; }
    #days-row, #cycle-row { height: auto; padding-top: 1; }
    #cycle-row Input { width: 8; }
    #cycle-row Label { padding: 1 1 0 1; }
    #buttons { padding-top: 1; height: auto; align-horizontal: right; }
    #buttons Button { margin-left: 1; }
    .hidden { display: none; }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        title: str = "New todo",
        initial: dict | None = None,
        candidates: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__()
        self._title = title
        self._initial = initial or {}
        self._candidates = candidates or []

    def compose(self) -> ComposeResult:
        init = self._initial
        repeat = init.get("repeat") or {}
        kind = repeat.get("kind", "none") if repeat else "none"
        days = set(repeat.get("days", [])) if kind == "days" else set()
        on_n = str(repeat.get("on", 1)) if kind == "cycle" else "1"
        off_n = str(repeat.get("off", 3)) if kind == "cycle" else "3"

        with Vertical(id="card"):
            yield Label(self._title, classes="title")

            yield Label("Text", classes="field")
            yield Input(value=init.get("text", ""), id="text", placeholder="What to do")

            yield Label("Max score (blank = none)", classes="field")
            ms = init.get("max_score")
            yield Input(value="" if ms is None else str(ms), id="score", placeholder="e.g. 10")

            yield Label("Repeat", classes="field")
            with RadioSet(id="repeat-kind"):
                yield RadioButton("None", value=(kind == "none"), id="r-none")
                yield RadioButton("Days of week", value=(kind == "days"), id="r-days")
                yield RadioButton("Cycle (N on / M off)", value=(kind == "cycle"), id="r-cycle")

            with Horizontal(id="days-row", classes="" if kind == "days" else "hidden"):
                yield DaysSelector(selected=days, id="days-selector")

            with Horizontal(id="cycle-row", classes="" if kind == "cycle" else "hidden"):
                yield Input(value=on_n, id="cycle-on", placeholder="on")
                yield Label("days on,")
                yield Input(value=off_n, id="cycle-off", placeholder="off")
                yield Label("days off")

            yield Label("Depends on (blank = none)", classes="field")
            dep_initial = init.get("depends_on")
            valid_lineages = {l for _, l in self._candidates}
            dep_value = dep_initial if dep_initial in valid_lineages else Select.NULL
            yield Select(
                options=self._candidates,
                value=dep_value,
                prompt="No prerequisite",
                allow_blank=True,
                id="depends-on",
            )

            yield Label("Project folder (blank = none)", classes="field")
            yield Input(value=init.get("folder") or "", id="folder", placeholder="/path/to/repo")

            with Horizontal(id="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Save", id="save", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#text", Input).focus()

    @on(RadioSet.Changed, "#repeat-kind")
    def _toggle_repeat(self, event: RadioSet.Changed) -> None:
        pid = event.pressed.id
        self.query_one("#days-row").set_class(pid != "r-days", "hidden")
        self.query_one("#cycle-row").set_class(pid != "r-cycle", "hidden")

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#save")
    def _save(self) -> None:
        text = self.query_one("#text", Input).value.strip()
        if not text:
            self.app.notify("Text is required.", severity="warning")
            return

        score_raw = self.query_one("#score", Input).value.strip()
        max_score: int | None = None
        if score_raw:
            try:
                max_score = int(score_raw)
                if max_score <= 0:
                    raise ValueError
            except ValueError:
                self.app.notify("Max score must be a positive integer.", severity="error")
                return

        kind_button = self.query_one("#repeat-kind", RadioSet).pressed_button
        kind_id = kind_button.id if kind_button else "r-none"
        repeat: dict | None = None
        if kind_id == "r-days":
            chosen = sorted(self.query_one("#days-selector", DaysSelector).selected)
            if not chosen:
                self.app.notify("Pick at least one day.", severity="error")
                return
            repeat = {"kind": "days", "days": chosen}
        elif kind_id == "r-cycle":
            try:
                on_v = int(self.query_one("#cycle-on", Input).value.strip())
                off_v = int(self.query_one("#cycle-off", Input).value.strip())
            except ValueError:
                self.app.notify("Cycle on/off must be integers.", severity="error")
                return
            if on_v < 1 or off_v < 0:
                self.app.notify("On must be ≥1, off must be ≥0.", severity="error")
                return
            anchor = self._initial.get("repeat", {}).get("anchor") if self._initial.get("repeat", {}).get("kind") == "cycle" else None
            repeat = {
                "kind": "cycle",
                "on": on_v,
                "off": off_v,
                "anchor": anchor or date.today().isoformat(),
            }

        folder_raw = self.query_one("#folder", Input).value.strip()
        folder: str | None = None
        if folder_raw:
            p = Path(folder_raw).expanduser()
            if not p.is_dir():
                self.app.notify(f"Not a directory: {p}", severity="error")
                return
            folder = str(p.resolve())

        dep_raw = self.query_one("#depends-on", Select).value
        depends_on = dep_raw if dep_raw != Select.NULL else None

        self.dismiss({
            "text": text,
            "max_score": max_score,
            "repeat": repeat,
            "folder": folder,
            "depends_on": depends_on,
        })


class SubtaskForm(ModalScreen[str | None]):
    """Add or edit a subtask. Dismisses with the new text or None."""

    CSS = """
    SubtaskForm { align: center middle; }
    #card {
        width: 56; height: auto; padding: 1 2;
        background: $panel; border: round $primary;
    }
    #card Label.title { color: $accent; text-style: bold; padding-bottom: 1; }
    #card Label.field { color: $text-muted; padding-top: 1; }
    #buttons { padding-top: 1; height: auto; align-horizontal: right; }
    #buttons Button { margin-left: 1; }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, title: str, initial_text: str = "") -> None:
        super().__init__()
        self._title = title
        self._initial = initial_text

    def compose(self) -> ComposeResult:
        with Vertical(id="card"):
            yield Label(self._title, classes="title")
            yield Label("Text", classes="field")
            yield Input(value=self._initial, id="text", placeholder="Subtask")
            with Horizontal(id="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Save", id="save", variant="primary")

    def on_mount(self) -> None:
        inp = self.query_one("#text", Input)
        inp.focus()

    @on(Input.Submitted, "#text")
    def _submit_on_enter(self) -> None:
        self._save()

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#save")
    def _save(self) -> None:
        text = self.query_one("#text", Input).value.strip()
        if not text:
            self.app.notify("Text is required.", severity="warning")
            return
        self.dismiss(text)
