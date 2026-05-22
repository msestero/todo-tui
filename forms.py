from __future__ import annotations

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


class _ItemForm(ModalScreen[dict | None]):
    """Shared modal for todos and subtasks. Dismisses with
    {"text": str, "folders": list[str], "claude_session_id": str | None}
    or None on cancel."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("up", "focus_previous", ""),
        ("down", "focus_next", ""),
    ]

    text_placeholder = "What to do"

    def __init__(self, initial: dict | None = None) -> None:
        super().__init__()
        self._initial = initial or {}

    def compose(self) -> ComposeResult:
        init = self._initial
        folders_value = ", ".join(init.get("folders") or [])

        with Vertical(id="card"):
            with Horizontal(classes="row"):
                yield Label("Text")
                yield Input(
                    value=init.get("text", ""),
                    id="text",
                    placeholder=self.text_placeholder,
                )
            with Horizontal(classes="row"):
                yield Label("Folders")
                yield Input(
                    value=folders_value,
                    id="folders",
                    placeholder="path/a, path/b",
                )
            with Horizontal(classes="row"):
                yield Label("Session")
                yield Input(
                    value=init.get("claude_session_id") or "",
                    id="session",
                    placeholder="Claude session id (optional)",
                )
            yield Label(_HINT, id="hint")

    def on_mount(self) -> None:
        self.query_one("#text", Input).focus()

    @on(Input.Submitted)
    def _save(self) -> None:
        text = self.query_one("#text", Input).value.strip()
        if not text:
            self.app.notify("Text is required.", severity="warning")
            return
        folders = _parse_folders(self.query_one("#folders", Input).value)
        session = self.query_one("#session", Input).value.strip() or None
        self.dismiss({"text": text, "folders": folders, "claude_session_id": session})

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
