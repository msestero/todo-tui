from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label

_FORM_CSS = """
$form-self { align: center middle; }
#card {
    width: auto; min-width: 52; height: auto; padding: 1 2;
    background: $panel; border: round $primary;
}
#card .row { height: 1; padding: 0; }
#card .row Label { width: 8; padding: 0 1 0 0; color: $text-muted; }
#card .row Input { width: 40; height: 1; border: none; padding: 0; background: $boost; }
#card .row Input:focus { background: $accent 20%; }
#hint { padding-top: 1; color: $text-muted; text-align: right; }
"""

_HINT = "[b]enter[/] save  ·  [b]esc[/] cancel"


def _parse_folders(raw: str) -> list[str]:
    return [chunk.strip() for chunk in raw.split(",") if chunk.strip()]


@dataclass
class ItemFormResult:
    """Typed payload returned by `_ItemForm`. Field names line up with
    `Todo.new` / `Subtask.new` kwargs so `Todo.new(**asdict(result))` works."""

    text: str = ""
    folders: list[str] = field(default_factory=list)
    claude_session_id: str | None = None


@dataclass(frozen=True)
class FieldSpec:
    """One row in the form. Drives both `compose` and `_save`.

    Adding a new field to the form is: append one `FieldSpec` to
    `_ItemForm.FIELDS` and add the matching attribute on `ItemFormResult`."""

    id: str
    label: str
    placeholder: str
    attr: str  # attribute on `ItemFormResult` this row reads/writes
    to_input: Callable[[ItemFormResult], str]
    from_input: Callable[[str], Any]


_FIELDS: list[FieldSpec] = [
    FieldSpec(
        id="text",
        label="Text",
        placeholder="What to do",
        attr="text",
        to_input=lambda r: r.text,
        from_input=lambda s: s.strip(),
    ),
    FieldSpec(
        id="folders",
        label="Folders",
        placeholder="path/a, path/b",
        attr="folders",
        to_input=lambda r: ", ".join(r.folders),
        from_input=_parse_folders,
    ),
    FieldSpec(
        id="session",
        label="Session",
        placeholder="Claude session id (optional)",
        attr="claude_session_id",
        to_input=lambda r: r.claude_session_id or "",
        from_input=lambda s: s.strip() or None,
    ),
]


class _ItemForm(ModalScreen["ItemFormResult | None"]):
    """Shared modal for todos and subtasks. Dismisses with `ItemFormResult`
    on save, `None` on cancel. Field layout is driven by `FIELDS`."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("up", "focus_previous", ""),
        ("down", "focus_next", ""),
    ]

    FIELDS: ClassVar[list[FieldSpec]] = _FIELDS
    text_placeholder = "What to do"

    def __init__(self, initial: ItemFormResult | None = None) -> None:
        super().__init__()
        self._initial = initial or ItemFormResult()

    def compose(self) -> ComposeResult:
        with Vertical(id="card"):
            for spec in self.FIELDS:
                placeholder = self.text_placeholder if spec.id == "text" else spec.placeholder
                with Horizontal(classes="row"):
                    yield Label(spec.label)
                    yield Input(
                        value=spec.to_input(self._initial),
                        id=spec.id,
                        placeholder=placeholder,
                    )
            yield Label(_HINT, id="hint")

    def on_mount(self) -> None:
        self.query_one(f"#{self.FIELDS[0].id}", Input).focus()

    @on(Input.Submitted)
    def _save(self) -> None:
        result = ItemFormResult()
        for spec in self.FIELDS:
            raw = self.query_one(f"#{spec.id}", Input).value
            setattr(result, spec.attr, spec.from_input(raw))
        if not result.text:
            self.app.notify("Text is required.", severity="warning")
            return
        self.dismiss(result)

    def action_cancel(self) -> None:
        self.dismiss(None)


class TodoForm(_ItemForm):
    CSS = _FORM_CSS.replace("$form-self", "TodoForm")
    text_placeholder = "What to do"


class SubtaskForm(_ItemForm):
    CSS = _FORM_CSS.replace("$form-self", "SubtaskForm")
    text_placeholder = "Subtask"


class NewFolderForm(ModalScreen[str | None]):
    """Prompt for a folder name; dismisses with the trimmed name or None."""

    CSS = _FORM_CSS.replace("$form-self", "NewFolderForm")

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="card"):
            with Horizontal(classes="row"):
                yield Label("Name")
                yield Input(id="name", placeholder="folder name in ~/TodoList/")
            yield Label(_HINT, id="hint")

    def on_mount(self) -> None:
        self.query_one("#name", Input).focus()

    @on(Input.Submitted, "#name")
    def _save(self) -> None:
        name = self.query_one("#name", Input).value.strip()
        if not name:
            self.app.notify("Name is required.", severity="warning")
            return
        self.dismiss(name)

    def action_cancel(self) -> None:
        self.dismiss(None)
