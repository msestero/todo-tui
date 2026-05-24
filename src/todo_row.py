from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.widgets import ListItem, Static

from row import Row


def row_key(row: Row) -> str:
    """Stable identity for a flattened row — used by the diff renderer to
    decide whether an existing widget can be reused in place of a new Row."""
    return f"{row.parent.id}:{row.sub.id if row.sub else ''}"


class TodoRow(ListItem):
    def __init__(self, row: Row) -> None:
        super().__init__()
        self.row = row
        self.key = row_key(row)
        self._static = Static(_render(row))

    def compose(self) -> ComposeResult:
        yield self._static

    def update_for(self, row: Row) -> None:
        """In-place content swap. Lets the parent ListView keep the existing
        widget node (no mount/unmount, no flicker) when the row's identity is
        the same but its presentation changed (done flag, collapsed indicator,
        etc.)."""
        self.row = row
        self._static.update(_render(row))


def _render(r: Row) -> str:
    if r.sub is None:
        text = escape(r.parent.text)
        suffix = _suffix(r)
        if r.parent.done:
            return f"[green]✔[/]  [strike dim]{text}[/]{suffix}"
        return f"[dim]○[/]  {text}{suffix}"
    text = escape(r.sub.text)
    if r.sub.done:
        return f"    [green]✔[/] [strike dim]{text}[/]"
    return f"    [dim]·[/] {text}"


def _suffix(r: Row) -> str:
    if r.collapsed:
        return f"  [dim cyan]({len(r.parent.subtasks)} hidden)[/]"
    if r.done_hidden:
        return f"  [dim cyan]({r.done_hidden} done hidden)[/]"
    return ""
