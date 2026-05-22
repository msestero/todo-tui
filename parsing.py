from __future__ import annotations

from datetime import date, timedelta


# Repeat is stored as one of:
#   None
#   {"kind": "days",  "days": [0..6, ...]}        # 0=Mon..6=Sun
#   {"kind": "cycle", "on": int, "off": int, "anchor": "YYYY-MM-DD"}
#
# Legacy string repeats ("daily"/"weekdays"/"weekly"/"<N>d") are migrated by
# `migrate_repeat` when loading from JSON.


def migrate_repeat(raw, todo_date: str | None) -> dict | None:
    """Convert any legacy string repeat into the structured dict form."""
    if raw is None or isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    s = raw.lower()
    if s == "daily":
        return {"kind": "days", "days": [0, 1, 2, 3, 4, 5, 6]}
    if s == "weekdays":
        return {"kind": "days", "days": [0, 1, 2, 3, 4]}
    if s == "weekly":
        anchor_d = date.fromisoformat(todo_date) if todo_date else date.today()
        return {"kind": "days", "days": [anchor_d.weekday()]}
    if s.endswith("d") and s[:-1].isdigit():
        n = int(s[:-1])
        anchor = todo_date or date.today().isoformat()
        return {"kind": "cycle", "on": 1, "off": max(0, n - 1), "anchor": anchor}
    return None


def repeat_label(repeat: dict | None) -> str:
    """Short human label used in the row view."""
    if not repeat:
        return ""
    if repeat["kind"] == "days":
        days = repeat.get("days", [])
        if len(days) == 7:
            return "daily"
        if days == [0, 1, 2, 3, 4]:
            return "weekdays"
        letters = "MTWRFSU"
        return "".join(letters[d] for d in sorted(days))
    if repeat["kind"] == "cycle":
        return f"{repeat['on']}on/{repeat['off']}off"
    return ""


def next_occurrence(repeat: dict, from_d: date) -> date:
    """Return the next scheduled date strictly after from_d."""
    if repeat["kind"] == "days":
        days = set(repeat.get("days", []))
        if not days:
            return from_d + timedelta(days=1)
        d = from_d + timedelta(days=1)
        for _ in range(8):
            if d.weekday() in days:
                return d
            d += timedelta(days=1)
        return from_d + timedelta(days=1)
    if repeat["kind"] == "cycle":
        on = max(1, int(repeat.get("on", 1)))
        off = max(0, int(repeat.get("off", 0)))
        period = on + off
        anchor = date.fromisoformat(repeat["anchor"])
        d = from_d + timedelta(days=1)
        for _ in range(period + 1):
            if ((d - anchor).days % period) < on:
                return d
            d += timedelta(days=1)
        return from_d + timedelta(days=1)
    return from_d + timedelta(days=1)
