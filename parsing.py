from __future__ import annotations

import re
from datetime import date, timedelta


REPEAT_RE = re.compile(r"\*(daily|weekdays|weekly|\d+d)\b", re.IGNORECASE)
SCORE_RE = re.compile(r"/(\d+)\b")


def parse_input(raw: str) -> tuple[str, str | None, int | None]:
    """Extract repeat and max_score tokens. Returns (clean_text, repeat, max_score)."""
    repeat = None
    max_score = None
    m = REPEAT_RE.search(raw)
    if m:
        repeat = m.group(1).lower()
        raw = raw[: m.start()] + raw[m.end():]
    m = SCORE_RE.search(raw)
    if m:
        max_score = int(m.group(1))
        raw = raw[: m.start()] + raw[m.end():]
    return raw.strip(), repeat, max_score


def next_occurrence(repeat: str, from_d: date) -> date:
    if repeat == "daily":
        return from_d + timedelta(days=1)
    if repeat == "weekly":
        return from_d + timedelta(days=7)
    if repeat == "weekdays":
        d = from_d + timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        return d
    m = re.fullmatch(r"(\d+)d", repeat)
    if m:
        return from_d + timedelta(days=int(m.group(1)))
    return from_d + timedelta(days=1)
