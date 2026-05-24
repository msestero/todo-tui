from __future__ import annotations

from datetime import date as date_cls

from textual.app import ComposeResult
from textual.widgets import ListItem, Static

from week_view import WeekRow


class WeekRowWidget(ListItem):
    """Sidebar row — either a week header (M/D-M/D) or an indented day under it."""

    def __init__(self, row: WeekRow) -> None:
        super().__init__()
        self.row = row

    def compose(self) -> ComposeResult:
        r = self.row
        if r.day is None:
            arrow = "▼" if r.expanded else "▶"
            yield Static(f"[dim]{arrow}[/] {r.week.label}")
        else:
            today = date_cls.today()
            marker = "[accent]●[/]" if r.day == today else "[dim]·[/]"
            yield Static(f"   {marker} {r.day.strftime('%a %m/%d')}")
