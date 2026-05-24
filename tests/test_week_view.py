from datetime import date

from week_view import Week, WeekViewState, build_week_rows, week_of


def test_week_of_monday_returns_same_week():
    w = week_of(date(2026, 5, 18))  # Monday
    assert w.start == date(2026, 5, 18)
    assert w.end == date(2026, 5, 24)


def test_week_of_sunday_returns_week_starting_prior_monday():
    w = week_of(date(2026, 5, 24))  # Sunday
    assert w.start == date(2026, 5, 18)
    assert w.end == date(2026, 5, 24)


def test_week_label_is_m_d_dash_m_d():
    assert week_of(date(2026, 5, 22)).label == "5/18-5/24"


def test_week_label_spans_month_boundary():
    w = week_of(date(2026, 4, 30))  # Thursday — week is 4/27-5/3
    assert w.label == "4/27-5/3"


def test_week_key_is_iso_of_monday():
    assert week_of(date(2026, 5, 24)).key == "2026-05-18"


def test_build_rows_collapses_all_weeks_by_default():
    rows = build_week_rows(["2026-05-22", "2026-05-15", "2026-05-08"], WeekViewState())
    assert len(rows) == 3
    assert all(r.day is None for r in rows)
    assert all(r.expanded is False for r in rows)


def test_build_rows_orders_weeks_newest_first():
    rows = build_week_rows(["2026-05-08", "2026-05-22", "2026-05-15"], WeekViewState())
    labels = [r.week.label for r in rows]
    assert labels == ["5/18-5/24", "5/11-5/17", "5/4-5/10"]


def test_dates_in_same_week_are_deduped():
    rows = build_week_rows(["2026-05-20", "2026-05-22", "2026-05-23"], WeekViewState())
    assert len(rows) == 1
    assert rows[0].week.label == "5/18-5/24"


def test_expanded_week_emits_seven_day_rows():
    state = WeekViewState(expanded_week="2026-05-18")
    rows = build_week_rows(["2026-05-22"], state)
    assert len(rows) == 8  # 1 header + 7 days
    assert rows[0].day is None
    assert rows[0].expanded is True
    days = [r.day for r in rows[1:]]
    assert days[0] == date(2026, 5, 18)  # Monday
    assert days[-1] == date(2026, 5, 24)  # Sunday


def test_only_one_week_can_be_expanded():
    """Two weeks in the input; state names only one. Just that one should have day rows."""
    state = WeekViewState(expanded_week="2026-05-18")
    rows = build_week_rows(["2026-05-22", "2026-05-15"], state)
    week_headers = [r for r in rows if r.day is None]
    day_rows = [r for r in rows if r.day is not None]
    assert len(week_headers) == 2
    assert len(day_rows) == 7
    # All day rows belong to the expanded week.
    assert all(r.week.key == "2026-05-18" for r in day_rows)


def test_empty_input_returns_empty_list():
    assert build_week_rows([], WeekViewState()) == []


def test_week_is_hashable():
    """Stored in a dict by key; the dataclass is frozen so it should be hashable too."""
    w = Week(start=date(2026, 5, 18), end=date(2026, 5, 24))
    assert hash(w) is not None
