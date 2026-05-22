from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.widgets import ListItem, Static

from row import Row


class TodoRow(ListItem):
    def __init__(self, row: Row) -> None:
        super().__init__()
        self.row = row

    def compose(self) -> ComposeResult:
        r = self.row
        if r.sub is None:
            text = escape(r.parent.text)
            if r.parent.done:
                yield Static(f"[green]✔[/]  [strike dim]{text}[/]")
            else:
                yield Static(f"[dim]○[/]  {text}")
        else:
            text = escape(r.sub.text)
            if r.sub.done:
                yield Static(f"    [green]✔[/] [strike dim]{text}[/]")
            else:
                yield Static(f"    [dim]·[/] {text}")
