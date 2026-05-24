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
            suffix = _suffix(r)
            if r.parent.done:
                yield Static(f"[green]✔[/]  [strike dim]{text}[/]{suffix}")
            else:
                yield Static(f"[dim]○[/]  {text}{suffix}")
        else:
            text = escape(r.sub.text)
            if r.sub.done:
                yield Static(f"    [green]✔[/] [strike dim]{text}[/]")
            else:
                yield Static(f"    [dim]·[/] {text}")


def _suffix(r: Row) -> str:
    if r.collapsed:
        return f"  [dim cyan]({len(r.parent.subtasks)} hidden)[/]"
    if r.done_hidden:
        return f"  [dim cyan]({r.done_hidden} done hidden)[/]"
    return ""
