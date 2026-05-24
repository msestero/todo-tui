"""Pure view-model for the week/day sidebar.

Groups a list of ISO date strings into Mon-Sun weeks, then flattens into rows
for a ListView. Only one week is expanded at a time; expanding a different week
implicitly collapses the previous one (the state holds a single `expanded_week`
key, not a set).

When a week is expanded its rows include all 7 days (Mon..Sun) — not just the
days that already have todos — so the user can also navigate to today or to
empty days within that week.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Week:
    start: date  # Monday
    end: date  # Sunday

    @property
    def key(self) -> str:
        """Stable id for the week (Monday's ISO date)."""
        return self.start.isoformat()

    @property
    def label(self) -> str:
        """Compact `M/D-M/D` label, e.g. '5/18-5/24'."""
        return f"{self.start.month}/{self.start.day}-{self.end.month}/{self.end.day}"


@dataclass
class WeekRow:
    week: Week
    day: date | None = None  # None = the week-header row; otherwise a day row.
    expanded: bool = False  # Only meaningful for week-header rows.


@dataclass
class WeekViewState:
    expanded_week: str | None = None  # Week.key of the currently-open week.


def week_of(d: date) -> Week:
    """Return the Mon-Sun week containing `d`."""
    start = d - timedelta(days=d.weekday())
    return Week(start=start, end=start + timedelta(days=6))


def build_week_rows(iso_dates: list[str], state: WeekViewState) -> list[WeekRow]:
    """Flatten the weeks spanned by `iso_dates` into a sidebar row list.

    Weeks are returned oldest first. The expanded week (if any) is followed by
    its 7 day rows in Mon..Sun order.
    """
    weeks = _unique_weeks(iso_dates)
    rows: list[WeekRow] = []
    for week in weeks:
        is_open = state.expanded_week == week.key
        rows.append(WeekRow(week=week, day=None, expanded=is_open))
        if is_open:
            rows.extend(WeekRow(week=week, day=week.start + timedelta(days=i)) for i in range(7))
    return rows


def _unique_weeks(iso_dates: list[str]) -> list[Week]:
    seen: dict[str, Week] = {}
    for iso in iso_dates:
        w = week_of(date.fromisoformat(iso))
        seen.setdefault(w.key, w)
    return sorted(seen.values(), key=lambda w: w.start)
