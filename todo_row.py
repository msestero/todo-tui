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
            extras = []
            if r.parent.subtasks:
                dc = sum(1 for s in r.parent.subtasks if s.done)
                extras.append(f"({dc}/{len(r.parent.subtasks)})")
            if r.parent.max_score is not None:
                sc = r.parent.score if r.parent.score is not None else "·"
                extras.append(f"{sc}/{r.parent.max_score}")
            if r.parent.repeat:
                extras.append(f"↻{r.parent.repeat}")
            tail = "  [dim]" + " ".join(extras) + "[/]" if extras else ""
            if r.parent.done:
                yield Static(f"[green]✔[/]  [strike dim]{text}[/]{tail}")
            else:
                yield Static(f"[dim]○[/]  {text}{tail}")
        else:
            text = escape(r.sub.text)
            if r.sub.done:
                yield Static(f"    [green]✔[/] [strike dim]{text}[/]")
            else:
                yield Static(f"    [dim]·[/] {text}")
