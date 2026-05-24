from __future__ import annotations

from datetime import date as date_cls

from textual.app import ComposeResult
from textual.widgets import ListItem, Static

from week_view import WeekRow


def week_row_key(row: WeekRow) -> str:
    """Stable identity for a sidebar row — week header or specific day."""
    return f"{row.week.key}:{row.day.isoformat() if row.day else ''}"


class WeekRowWidget(ListItem):
    """Sidebar row — either a week header (M/D-M/D) or an indented day under it."""

    def __init__(self, row: WeekRow) -> None:
        super().__init__()
        self.row = row
        self.key = week_row_key(row)
        self._static = Static(_render(row))

    def compose(self) -> ComposeResult:
        yield self._static

    def update_for(self, row: WeekRow) -> None:
        self.row = row
        self._static.update(_render(row))


def _render(r: WeekRow) -> str:
    if r.day is None:
        arrow = "▼" if r.expanded else "▶"
        return f"[dim]{arrow}[/] {r.week.label}"
    today = date_cls.today()
    marker = "[accent]●[/]" if r.day == today else "[dim]·[/]"
    return f"   {marker} {r.day.strftime('%a %m/%d')}"
